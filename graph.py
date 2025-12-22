from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from schemas import (HighLevelDesign, LowLevelDesign, JudgeVerdict, 
                     ScaffoldingSpec, RunMetrics)
import agents
import tools
from tests import quality
from model_factory import get_llm
from callbacks import TokenMeter, LogCollector

class AgentState(TypedDict):
    user_request: str
    provider: str
    api_key: str
    hld: Optional[HighLevelDesign]
    lld: Optional[LowLevelDesign]
    verdict: Optional[JudgeVerdict]
    scaffold: Optional[ScaffoldingSpec]
    diagram_code: Optional[str]
    diagram_path: Optional[str]
    metrics: Optional[Dict[str, Any]]
    retry_count: int
    total_tokens: int
    logs: List[Dict]

def manager_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    logger = LogCollector()
    
    feedback = ""
    if state.get('verdict') and not state['verdict'].is_valid:
        feedback = state['verdict'].critique
        logger.log("Manager", f"Refining HLD based on feedback: {feedback}")
    else:
        logger.log("Manager", "Drafting HLD with RAG...")

    hld = agents.engineering_manager(state['user_request'], llm, meter, feedback)
    logger.log("Manager", "HLD Generated.")
    
    return {
        "hld": hld, 
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs 
    }

def security_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    logger = LogCollector()
    
    logger.log("Security", "Reviewing HLD Security...")
    improved_security = agents.security_specialist(state['hld'], llm, meter)
    
    current_hld = state['hld']
    current_hld.security_compliance = improved_security
    
    return {
        "hld": current_hld,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs
    }

def lead_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    logger = LogCollector()
    
    logger.log("Team Lead", "Drafting LLD...")
    lld = agents.team_lead(state['hld'], llm, meter)
    
    return {
        "lld": lld,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs
    }

def judge_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    logger = LogCollector()
    
    logger.log("Judge", "Evaluating Consistency...")
    verdict = agents.architecture_judge(state['hld'], state['lld'], llm, meter)
    
    status = "Approved" if verdict.is_valid else "Rejected"
    logger.log("Judge", f"Verdict: {status}")
    
    return {
        "verdict": verdict, 
        "retry_count": state["retry_count"] + 1,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs
    }

def visuals_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    logger = LogCollector()
    
    logger.log("Visuals", "Generating Diagrams-as-Code...")
    diagram_spec = agents.visual_architect(state['hld'], llm, meter)
    
    # Execute Code
    image_path = tools.run_diagram_code(diagram_spec.python_code)
    
    return {
        "diagram_code": diagram_spec.python_code,
        "diagram_path": image_path,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs
    }

def scaffold_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    logger = LogCollector()
    
    logger.log("Builder", "Scaffolding Project...")
    scaffold = agents.scaffold_architect(state['hld'], state['lld'], llm, meter)
    
    return {
        "scaffold": scaffold,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs
    }

def quality_node(state: AgentState):
    logger = LogCollector()
    logger.log("Quality", "Running DeepEval & Red Teaming...")
    
    hld_json = state['hld'].model_dump_json()
    eval_res = quality.evaluate_design(state['user_request'], hld_json)
    issues = quality.red_team_probe(hld_json)
    
    metrics = {
        "security_score": eval_res['security_score'],
        "security_reason": eval_res['security_reason'],
        "red_team_issues": issues
    }
    
    return {
        "metrics": metrics,
        "logs": state.get("logs", []) + logger.logs
    }

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
workflow.add_node("scaffold", scaffold_node)
workflow.add_node("quality", quality_node)

workflow.set_entry_point("manager")
workflow.add_edge("manager", "security")
workflow.add_edge("security", "team_lead")
workflow.add_edge("team_lead", "judge")

workflow.add_conditional_edges("judge", check_quality, {
    "approved": "visuals",
    "rejected": "manager"
})

workflow.add_edge("visuals", "scaffold")
workflow.add_edge("scaffold", "quality")
workflow.add_edge("quality", END)

app_graph = workflow.compile()