from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from schemas import (HighLevelDesign, LowLevelDesign, JudgeVerdict, 
                     ScaffoldingSpec, DiagramCode, DiagramValidationResult)
import agents
import tools
from model_factory import get_llm
from callbacks import TokenMeter, LogCollector

# --- State Definition ---
class AgentState(TypedDict):
    user_request: str
    provider: str
    api_key: str
    
    # Artifacts
    hld: Optional[HighLevelDesign]
    lld: Optional[LowLevelDesign]
    verdict: Optional[JudgeVerdict]
    scaffold: Optional[ScaffoldingSpec]
    
    # Diagram Artifacts
    diagram_code: Optional[DiagramCode]
    diagram_path: Optional[str]
    diagram_validation: Optional[DiagramValidationResult]
    
    # Metrics & Logs
    retry_count: int
    total_tokens: int
    logs: List[Dict]
    scaffold_logs: Optional[List[str]]

# --- Nodes ---

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
    llm = get_llm(state['provider'], state['api_key'], "smart") # Diagrams need smart model
    meter = TokenMeter()
    logger = LogCollector()
    
    logger.log("Visuals", "Generating Diagrams-as-Code...")
    
    # 1. Generate the Code using the correct agent function
    diagram_spec = agents.visual_architect(state['hld'], llm, meter)
    
    # 2. Execute the Code using the Tool
    image_path = tools.run_diagram_code(diagram_spec.python_code)
    
    if "Error" not in image_path:
        logger.log("Visuals", f"Diagram rendered: {image_path}")
    else:
        logger.log("Visuals", f"Diagram execution failed: {image_path}")
    
    return {
        "diagram_code": diagram_spec, # Store the DiagramCode object
        "diagram_path": image_path,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs
    }

def validator_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "fast")
    meter = TokenMeter()
    logger = LogCollector()
    
    # Only validate if we successfully generated code
    if state.get('diagram_code'):
        logger.log("Validator", "Checking Diagram Consistency...")
        
        # Inject the generated diagrams back into HLD for validation context
        # (This uses the Pydantic copy method to avoid mutating the original state reference too early)
        temp_hld = state['hld'].model_copy()
        
        # NOTE: We assume visual_architect returned ArchitectureDiagrams (or DiagramCode that matches)
        # If your schema uses 'diagrams' field in HLD, we populate it here for the validator.
        # Since 'visual_architect' returns 'ArchitectureDiagrams' in previous turns, we map it.
        # If it returns 'DiagramCode' (single string), we wrap it or pass it directly.
        # Based on your agents.py: visual_architect returns ArchitectureDiagrams.
        
        # temp_hld.diagrams = state['diagram_code'] 
        
        # Call the validator agent
        validation = agents.diagram_validator(temp_hld, llm, meter)
        
        if not validation.valid_syntax:
            logger.log("Validator", f"Issues Found: {validation.critique}")
        else:
            logger.log("Validator", "Diagram logic is valid.")
            
        return {
            "diagram_validation": validation,
            "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
            "logs": state.get("logs", []) + logger.logs
        }
    
    return {"logs": state.get("logs", []) + logger.logs}

def scaffold_node(state: AgentState):
    llm = get_llm(state['provider'], state['api_key'], "smart")
    meter = TokenMeter()
    logger = LogCollector()
    
    logger.log("Builder", "Planning Project Scaffolding...")
    scaffold_spec = agents.scaffold_architect(state['hld'], state['lld'], llm, meter)
    
    logger.log("Builder", "Writing files to disk...")
    logs = tools.generate_scaffold(scaffold_spec)
    
    return {
        "scaffold": scaffold_spec,
        "scaffold_logs": logs,
        "total_tokens": state.get("total_tokens", 0) + meter.total_tokens,
        "logs": state.get("logs", []) + logger.logs
    }

# --- Conditional Logic ---

def check_quality(state: AgentState):
    # Retry logic
    if state['verdict'].is_valid or state['retry_count'] > 2:
        return "approved"
    return "rejected"

# --- Graph Definition ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("manager", manager_node)
workflow.add_node("security", security_node)
workflow.add_node("team_lead", lead_node)
workflow.add_node("judge", judge_node)
workflow.add_node("visuals", visuals_node)
workflow.add_node("validator", validator_node)
workflow.add_node("scaffold", scaffold_node)

# Define Edges
workflow.set_entry_point("manager")
workflow.add_edge("manager", "security")
workflow.add_edge("security", "team_lead")
workflow.add_edge("team_lead", "judge")

# Conditional: Judge approves -> Visuals; Judge rejects -> Manager
workflow.add_conditional_edges(
    "judge", 
    check_quality, 
    {
        "approved": "visuals",
        "rejected": "manager"
    }
)

# Linear flow after approval
workflow.add_edge("visuals", "validator") # Generate -> Validate
workflow.add_edge("validator", "scaffold")
workflow.add_edge("scaffold", END)

app_graph = workflow.compile()