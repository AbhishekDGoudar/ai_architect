from langchain_core.language_models import BaseChatModel
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict
from callbacks import TokenMeter

def engineering_manager(user_request: str, llm: BaseChatModel, meter: TokenMeter):
    system_msg = """
    You are a Senior Software Architect. 
    Analyze the request. Prioritize Scalability, Security, and Cost.
    """
    structured_llm = llm.with_structured_output(HighLevelDesign)
    
    # We pass the meter via the 'callbacks' config
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_request)],
        config={"callbacks": [meter]}
    )

def team_lead(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter, feedback: str = ""):
    hld_context = hld.model_dump_json(indent=2)
    system_msg = f"""
    You are a Senior Team Lead. Convert this HLD into an implementation plan.
    ARCHITECT'S DESIGN: {hld_context}
    {f"⚠️ PREVIOUS REJECTION FEEDBACK: {feedback}" if feedback else ""}
    """
    structured_llm = llm.with_structured_output(LowLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate LLD")],
        config={"callbacks": [meter]}
    )

def architecture_judge(hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    system_msg = "You are a QA Architect. Verify consistency between HLD and LLD."
    structured_llm = llm.with_structured_output(JudgeVerdict)
    
    user_content = f"HLD:\n{hld.model_dump_json()}\n\nLLD:\n{lld.model_dump_json()}"
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_content)],
        config={"callbacks": [meter]}
    )