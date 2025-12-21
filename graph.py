from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict
import agents
from model_factory import get_llm
from callbacks import TokenMeter

class AgentState(TypedDict):
    user_request: str
    provider: str
    api_key: str
    hld: Optional[HighLevelDesign]
    lld: Optional[LowLevelDesign]
    verdict: Optional[JudgeVerdict]
    retry_count: int
    # Metrics
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int

def manager_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    hld = agents.engineering_manager(state['user_request'], llm, meter)
    return {
        "hld": hld, "retry_count": 0,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "prompt_tokens": state.get("prompt_tokens", 0) + meter.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + meter.completion_tokens
    }

def lead_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    feedback = state['verdict'].critique if (state.get('verdict') and not state['verdict'].is_valid) else ""
    lld = agents.team_lead(state['hld'], llm, meter, feedback)
    return {
        "lld": lld,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "prompt_tokens": state.get("prompt_tokens", 0) + meter.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + meter.completion_tokens
    }

def judge_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    verdict = agents.architecture_judge(state['hld'], state['lld'], llm, meter)
    return {
        "verdict": verdict, "retry_count": state["retry_count"] + 1,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "prompt_tokens": state.get("prompt_tokens", 0) + meter.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + meter.completion_tokens
    }

def check_quality(state: AgentState):
    if state['verdict'].is_valid or state['retry_count'] > 3:
        return "approved"
    return "rejected"

workflow = StateGraph(AgentState)
workflow.add_node("manager", manager_node)
workflow.add_node("team_lead", lead_node)
workflow.add_node("judge", judge_node)

workflow.set_entry_point("manager")
workflow.add_edge("manager", "team_lead")
workflow.add_edge("team_lead", "judge")
workflow.add_conditional_edges("judge", check_quality, {"approved": END, "rejected": "team_lead"})

app_graph = workflow.compile()