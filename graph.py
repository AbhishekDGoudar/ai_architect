from typing import TypedDict, Optional, List, Dict
from langgraph.graph import StateGraph, END
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict
import agents
from model_factory import get_llm
from callbacks import TokenMeter, LogCollector

class AgentState(TypedDict):
    user_request: str
    provider: str
    api_key: str
    hld: Optional[HighLevelDesign]
    lld: Optional[LowLevelDesign]
    verdict: Optional[JudgeVerdict]
    retry_count: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    logs: List[Dict]

def manager_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    logger = LogCollector()
    
    # Check for previous feedback
    feedback = ""
    if state.get('verdict') and not state['verdict'].is_valid:
        feedback = state['verdict'].critique
        logger.log("Manager", f"Refining HLD based on feedback: {feedback}")
    else:
        logger.log("Manager", "Drafting HLD...")

    hld = agents.engineering_manager(state['user_request'], llm, meter, feedback)
    logger.log("Manager", "HLD Generated.")
    
    return {
        "hld": hld, 
        # Reset retry count if we are starting a fresh loop, or increment? 
        # Actually we keep retry_count from increasing indefinitely in the conditional edge
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs 
    }

def security_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    logger = LogCollector()
    
    logger.log("Security", "Reviewing HLD Security Compliance...")
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
    
    logger.log("Judge", "Evaluating Consistency & Diagrams...")
    verdict = agents.architecture_judge(state['hld'], state['lld'], llm, meter)
    
    status = "Approved" if verdict.is_valid else "Rejected"
    logger.log("Judge", f"Verdict: {status}")
    
    return {
        "verdict": verdict, 
        "retry_count": state["retry_count"] + 1,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs
    }

def check_quality(state: AgentState):
    if state['verdict'].is_valid or state['retry_count'] > 3:
        return "approved"
    return "rejected"

workflow = StateGraph(AgentState)
workflow.add_node("manager", manager_node)
workflow.add_node("security", security_node)
workflow.add_node("team_lead", lead_node)
workflow.add_node("judge", judge_node)

workflow.set_entry_point("manager")
workflow.add_edge("manager", "security")
workflow.add_edge("security", "team_lead")
workflow.add_edge("team_lead", "judge")

# Critical Change: Rejection goes back to Manager to fix HLD/Diagrams
workflow.add_conditional_edges("judge", check_quality, {"approved": END, "rejected": "manager"})

app_graph = workflow.compile()