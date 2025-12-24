from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from schemas import (HighLevelDesign, LowLevelDesign, JudgeVerdict, 
                     DiagramValidationResult, ArchitectureDiagrams, ProjectStructure)
import agents
import tools
from model_factory import get_llm
from callbacks import TokenMeter

class AgentState(TypedDict):
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

# --- Nodes ---

def manager_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    hld = agents.engineering_manager(state['user_request'], llm, meter, feedback="")
    return {
        "hld": hld, 
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Manager", "message": "HLD Drafted"}]
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
        "logs": [{"role": "Security", "message": "Security Hardened"}]
    }

def lead_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    lld = agents.team_lead(state['hld'], llm, meter)
    return {
        "lld": lld, 
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Lead", "message": "LLD Created"}]
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
        "retry_count": state["retry_count"] + 1, 
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Refiner", "message": "Design Refined"}]
    }

def visuals_node(state: AgentState):
    # Uses FAST model to generate Python Diagram Code
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    diagram_spec = agents.visual_architect(state['hld'], llm, meter)
    
    # Immediately render the diagram
    code_to_render = diagram_spec.container_diagram or diagram_spec.system_context
    image_path = tools.run_diagram_code(code_to_render)
    
    return {
        "diagram_code": diagram_spec, 
        "diagram_path": image_path, 
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Visuals", "message": "Diagrams Generated & Rendered"}]
    }

def validator_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    temp_hld = state['hld'].model_copy()
    temp_hld.diagrams = state['diagram_code']
    validation = agents.diagram_validator(temp_hld, llm, meter)
    return {
        "diagram_validation": validation, 
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens
    }

def check_quality(state: AgentState):
    if state['verdict'].is_valid:
        return "approved"
    if state['retry_count'] > 2:
        return "max_retries"
    return "rejected"

# --- Workflow ---
workflow = StateGraph(AgentState)

workflow.add_node("manager", manager_node)
workflow.add_node("security", security_node)
workflow.add_node("team_lead", lead_node)
workflow.add_node("judge", judge_node)
workflow.add_node("refiner", refiner_node)
workflow.add_node("visuals", visuals_node)
workflow.add_node("validator", validator_node)

workflow.set_entry_point("manager")
workflow.add_edge("manager", "security")
workflow.add_edge("security", "team_lead")
workflow.add_edge("team_lead", "judge")

workflow.add_conditional_edges(
    "judge", 
    check_quality, 
    {
        "rejected": "refiner",
        "approved": "visuals",     # Go straight to Visuals on approval
        "max_retries": "visuals"
    }
)

workflow.add_edge("refiner", "judge")
workflow.add_edge("visuals", "validator")
workflow.add_edge("validator", END) # End graph here. Scaffolding is manual.

app_graph = workflow.compile()