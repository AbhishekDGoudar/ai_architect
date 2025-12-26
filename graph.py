from typing import TypedDict, Optional, List, Dict, Literal
from datetime import date
from langgraph.graph import StateGraph, END, START
from schemas import (
    HighLevelDesign, LowLevelDesign, JudgeVerdict, 
    DiagramValidationResult, ArchitectureDiagrams, ProjectStructure
)
import agents
import tools
from model_factory import get_llm
from callbacks import TokenMeter
from tools import run_diagram
import asyncio
# ==========================================
# Agent State
# ==========================================

class AgentState(TypedDict):
    task: Literal["architecture", "diagrams", "code"] 
    user_request: str
    provider: str
    api_key: str
    hld: Optional[HighLevelDesign]
    lld: Optional[LowLevelDesign]
    verdict: Optional[JudgeVerdict]
    diagram_code: Optional[ArchitectureDiagrams]
    diagram_path: Optional[str]
    diagram_validation: Optional[DiagramValidationResult]
    scaffold: Optional[ProjectStructure]
    retry_count: int
    total_tokens: int
    logs: List[Dict]
    generated_date: str

# ==========================================
# 🧩 Nodes
# ==========================================

def manager_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    today = date.today().isoformat()
    
    hld = agents.engineering_manager(
        user_request=state['user_request'], 
        llm=llm, 
        meter=meter, 
        feedback=f"Use tech stack current as of {today}"
    )
    
    return {
        "hld": hld,
        "generated_date": today,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Manager", "message": "HLD drafted"}]
    }

def security_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    improved_security = agents.security_specialist(state['hld'], llm, meter)
    current_hld = state['hld'].model_copy()
    current_hld.security_compliance = improved_security
    return {
        "hld": current_hld,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Security", "message": "Security hardened"}]
    }

def lead_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    lld = agents.team_lead(state['hld'], llm, meter)
    return {
        "lld": lld,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Lead", "message": "LLD created"}]
    }

def judge_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    verdict = agents.architecture_judge(state['hld'], state['lld'], llm, meter)
    return {
        "verdict": verdict,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Judge", "message": f"Verdict: {'Approved' if verdict.is_valid else 'Rejected'}"}]
    }

def refiner_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    refined = agents.reiteration_agent(state['verdict'], state['hld'], state['lld'], llm, meter)
    return {
        "hld": refined.hld,
        "lld": refined.lld,
        "retry_count": state.get("retry_count", 0) + 1,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Refiner", "message": "Design refined"}]
    }



def visuals_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    
    # Generate the initial diagram code using visual_architect
    diagram_spec = agents.visual_architect(state['hld'], llm, meter)
    diagrams = diagram_spec
    diagram_fields = ['system_context', 'container_diagram', 'data_flow']

    # Collect all three fields and their respective error messages
    codes = {field: getattr(diagrams, field) for field in diagram_fields}
    errors = {field: asyncio.run(run_diagram(codes[field])) for field in diagram_fields}

    # If any error occurs, pass all three diagrams and errors to diagram_fixer
    fixed_diagrams = agents.diagram_fixer(
        system_context_code=codes['system_context'], 
        container_diagram_code=codes['container_diagram'], 
        data_flow_code=codes['data_flow'],
        system_context_error=errors['system_context'], 
        container_diagram_error=errors['container_diagram'], 
        data_flow_error=errors['data_flow'],
        llm=llm, meter=meter
    )
    
    return {
        "diagram_code": fixed_diagrams,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Visuals", "message": "Diagrams generated and validated"}]
    }


def scaffold_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    scaffold = agents.scaffold_architect(state['lld'], llm, meter)
    return {
        "scaffold": scaffold,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Scaffold", "message": "Project scaffold generated"}]
    }

# ==========================================
# Conditional Routing Logic
# ==========================================

def route_entry_point(state: AgentState):
    task = state.get('task', 'architecture')
    if task == 'diagrams':
        return 'visuals'
    elif task == 'code':
        return 'scaffold'
    return 'manager'

def check_quality(state: AgentState):
    if state['verdict'] and state['verdict'].is_valid:
        return "approved"
    if state.get('retry_count', 0) > 2:
        return "max_retries"
    return "rejected"

# ==========================================
# Workflow Definition
# ==========================================

workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("manager", manager_node)
workflow.add_node("security", security_node)
workflow.add_node("team_lead", lead_node)
workflow.add_node("judge", judge_node)
workflow.add_node("refiner", refiner_node)
workflow.add_node("visuals", visuals_node)
workflow.add_node("scaffold", scaffold_node)

# Routing
workflow.add_conditional_edges(
    START,
    route_entry_point,
    {
        "manager": "manager",
        "visuals": "visuals",
        "scaffold": "scaffold"
    }
)

# Architecture flow
workflow.add_edge("manager", "security")
workflow.add_edge("security", "team_lead")
workflow.add_edge("team_lead", "judge")
workflow.add_conditional_edges(
    "judge",
    check_quality,
    {"rejected": "refiner", "approved": END, "max_retries": END}
)
workflow.add_edge("refiner", "judge")

# Diagram flow
workflow.add_edge("visuals", END)  # Already validated inside visuals_node

# Code flow
workflow.add_edge("scaffold", END)

# Compile
app_graph = workflow.compile()
