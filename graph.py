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
    # Security hardens the HLD
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
    # Lead creates LLD from HLD
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
    # REMOVED: llm = get_llm(...) 
    # REMOVED: diagram_spec = agents.visual_architect(...)
    
    # NEW: Deterministic Generation
    # We construct the object manually using the tool we just wrote
    mermaid_code = tools.hld_to_mermaid(state['hld'])
    
    # Wrap it in the Schema so the UI can read it
    from schemas import ArchitectureDiagrams
    diagram_spec = ArchitectureDiagrams(
        system_context=mermaid_code["system_context"],
        container_diagram=mermaid_code["container_diagram"],
        data_flow=mermaid_code["data_flow"]
    )
    
    # Save files (Optional, since we have the string in memory)
    paths = []
    paths.append(tools.run_diagram_code(diagram_spec.system_context, "system_context"))
    paths.append(tools.run_diagram_code(diagram_spec.container_diagram, "container_diagram"))
    paths.append(tools.run_diagram_code(diagram_spec.data_flow, "data_flow"))
    
    return {
        "diagram_code": diagram_spec,
        "diagram_path": paths,
        "total_tokens": state.get("total_tokens", 0), # No tokens used!
        "logs": [{"role": "Visuals", "message": "Diagrams generated deterministically"}]
    }

def fix_diagram_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    
    # Identify which code block failed (simplification: sending context)
    failed_code = state['diagram_code'].container_diagram or state['diagram_code'].system_context
    error_msg = state['diagram_path']
    
    fixed_diagrams = agents.diagram_fixer(failed_code, error_msg, llm, meter)
    
    paths = []
    for code in [fixed_diagrams.system_context, fixed_diagrams.container_diagram, fixed_diagrams.data_flow]:
        if code:
            paths.append(tools.run_diagram_code(code))
    
    return {
        "diagram_code": fixed_diagrams,
        "diagram_path": paths,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": [{"role": "Fixer", "message": "Diagram fix attempted"}]
    }

def validator_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    
    if state.get('hld'):
        temp_hld = state['hld'].model_copy()
        temp_hld.diagrams = state.get('diagram_code')
        validation = agents.diagram_validator(temp_hld, llm, meter)
    else:
        validation = DiagramValidationResult(is_valid=False, reason="Missing HLD context")

    return {
        "diagram_validation": validation,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens
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
# 🔄 Conditional Logic
# ==========================================

def route_entry_point(state: AgentState):
    """Determines the starting node based on the user's task."""
    task = state.get('task', 'architecture')
    if task == 'diagrams':
        return 'visuals'
    elif task == 'code':
        return 'scaffold'
    return 'manager'

def check_diagram_execution(state: AgentState):
    result = state.get('diagram_path')
    if result:
        results_to_check = result if isinstance(result, list) else [result]
        if any(("Error" in str(r) or "Exception" in str(r)) for r in results_to_check):
            if state.get('retry_count', 0) > 3:
                return "failed"
            return "error"
    return "success"

def check_quality(state: AgentState):
    # If approved, we STOP (return END). 
    # Diagrams and Code are now manual subsequent steps.
    if state['verdict'] and state['verdict'].is_valid:
        return "approved" 
    
    if state.get('retry_count', 0) > 2:
        return "max_retries"
        
    return "rejected"

# ==========================================
# 🧩 Workflow Definition
# ==========================================

workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("manager", manager_node)
workflow.add_node("security", security_node)
workflow.add_node("team_lead", lead_node)
workflow.add_node("judge", judge_node)
workflow.add_node("refiner", refiner_node)
workflow.add_node("visuals", visuals_node)
workflow.add_node("fix_diagram", fix_diagram_node)
workflow.add_node("validator", validator_node)
workflow.add_node("scaffold", scaffold_node)

# --- Routing ---
workflow.add_conditional_edges(
    START,
    route_entry_point,
    {
        "manager": "manager",
        "visuals": "visuals",
        "scaffold": "scaffold"
    }
)

# --- Architecture Flow (Task 1) ---
workflow.add_edge("manager", "security")
workflow.add_edge("security", "team_lead")
workflow.add_edge("team_lead", "judge")

workflow.add_conditional_edges(
    "judge",
    check_quality,
    {
        "rejected": "refiner", 
        "approved": END,      # STOPS HERE
        "max_retries": END    # STOPS HERE
    }
)
workflow.add_edge("refiner", "judge")

# --- Diagram Flow (Task 2) ---
workflow.add_conditional_edges(
    "visuals",
    check_diagram_execution,
    {
        "success": "validator", 
        "error": "fix_diagram", 
        "failed": "validator"
    }
)
workflow.add_conditional_edges(
    "fix_diagram",
    check_diagram_execution,
    {
        "success": "validator", 
        "error": "fix_diagram", 
        "failed": "validator"
    }
)
workflow.add_edge("validator", END)

# --- Code Flow (Task 3) ---
workflow.add_edge("scaffold", END)

# Compile
app_graph = workflow.compile()