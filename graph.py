from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from schemas import (HighLevelDesign, LowLevelDesign, JudgeVerdict, 
                     DiagramValidationResult, ArchitectureDiagrams)
import agents
import tools
from model_factory import get_llm
from callbacks import TokenMeter, LogCollector

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
    retry_count: int
    total_tokens: int
    logs: List[Dict]

def manager_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    logger = LogCollector()
    feedback = state['verdict'].critique if state.get('verdict') and not state['verdict'].is_valid else ""
    hld = agents.engineering_manager(state['user_request'], llm, meter, feedback)
    return {"hld": hld, "total_tokens": state.get("total_tokens", 0) + meter.total_tokens, "logs": state.get("logs", []) + [{"role": "Manager", "message": "HLD Generated"}]}

def security_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    improved_security = agents.security_specialist(state['hld'], llm, meter)
    current_hld = state['hld']
    current_hld.security_compliance = improved_security
    return {"hld": current_hld, "total_tokens": state.get("total_tokens", 0) + meter.total_tokens}

def lead_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    lld = agents.team_lead(state['hld'], llm, meter)
    return {"lld": lld, "total_tokens": state.get("total_tokens", 0) + meter.total_tokens}

def judge_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    verdict = agents.architecture_judge(state['hld'], state['lld'], llm, meter)
    return {"verdict": verdict, "retry_count": state["retry_count"] + 1, "total_tokens": state.get("total_tokens", 0) + meter.total_tokens}

def visuals_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    diagram_spec = agents.visual_architect(state['hld'], llm, meter)
    code_to_render = diagram_spec.container_diagram or diagram_spec.system_context
    image_path = tools.run_diagram_code(code_to_render)
    return {"diagram_code": diagram_spec, "diagram_path": image_path, "total_tokens": state.get("total_tokens", 0) + meter.total_tokens}

def validator_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    temp_hld = state['hld'].model_copy()
    temp_hld.diagrams = state['diagram_code']
    validation = agents.diagram_validator(temp_hld, llm, meter)
    return {"diagram_validation": validation, "total_tokens": state.get("total_tokens", 0) + meter.total_tokens}

def check_quality(state: AgentState):
    if state['verdict'].is_valid or state['retry_count'] > 2:
        return "approved"
    return "rejected"

workflow = StateGraph(AgentState)
workflow.add_node("manager", manager_node)
workflow.add_node("security", security_node)
workflow.add_node("team_lead", lead_node)
workflow.add_node("judge", judge_node)
workflow.add_node("visuals", visuals_node)
workflow.add_node("validator", validator_node)

workflow.set_entry_point("manager")
workflow.add_edge("manager", "security")
workflow.add_edge("security", "team_lead")
workflow.add_edge("team_lead", "judge")
workflow.add_conditional_edges("judge", check_quality, {"approved": "visuals", "rejected": "manager"})
workflow.add_edge("visuals", "validator")
workflow.add_edge("validator", END)

app_graph = workflow.compile()