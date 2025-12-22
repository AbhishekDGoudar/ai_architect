from langchain_core.language_models import BaseChatModel
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict, SecurityCompliance
from callbacks import TokenMeter

def engineering_manager(user_request: str, llm: BaseChatModel, meter: TokenMeter, feedback: str = ""):
    system_msg = """
    You are a Principal Software Architect. 
    Design a robust High Level Design (HLD) covering points 1 to 11 of our standard framework.
    
    INSTRUCTIONS
    1 Fill the architecture_overview with clear TEXT descriptions
    2 Fill the new diagrams section with valid MERMAID JS code
       For Context Use graph TD
       For Data Flow Use sequenceDiagram
    
    Prioritize Scalability Security and Cost
    """
    
    if feedback:
        system_msg += f"\n\n⚠️ PREVIOUS REJECTION FEEDBACK: {feedback}\nFix the design or diagrams based on this feedback."

    structured_llm = llm.with_structured_output(HighLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_request)],
        config={"callbacks": [meter]}
    )

def security_specialist(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    hld_context = hld.model_dump_json(indent=2)
    
    system_msg = f"""
    You are a generic Security Specialist (InfoSec).
    Review the 'security_compliance' section of the HLD below.
    Refine it to meet strict standards (GDPR/SOC2 if applicable, Threat Modeling, Zero Trust).
    
    CURRENT HLD:
    {hld_context}
    
    Output a vastly improved 'SecurityCompliance' object.
    """
    structured_llm = llm.with_structured_output(SecurityCompliance)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Harden this security design.")],
        config={"callbacks": [meter]}
    )

def team_lead(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    hld_context = hld.model_dump_json(indent=2)
    system_msg = f"""
    You are a Senior Team Lead. 
    Based on the HLD, generate the Low Level Design (LLD) covering points 12 to 22.
    
    Focus on Internal Class Design API Contracts Data Models (Indexes/Constraints) and Failure Modes.
    
    ARCHITECT'S DESIGN: 
    {hld_context}
    """
    structured_llm = llm.with_structured_output(LowLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate LLD")],
        config={"callbacks": [meter]}
    )

def architecture_judge(hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    system_msg = """
    You are a QA Architect. 
    Verify consistency between HLD and LLD.
    
    CRITICAL DIAGRAM VERIFICATION
    1 Check the 'diagrams' field in HLD.
    2 Verify the Mermaid JS syntax is valid.
    3 Ensure the text labels in the diagrams match the component names.
    4 If the Mermaid code looks broken or incomplete mark is_valid as False.

    GENERAL CHECKS
    1 LLD components match HLD components.
    2 Security implementation in LLD matches HLD compliance rules.
    """
    structured_llm = llm.with_structured_output(JudgeVerdict)
    
    user_content = f"HLD:\n{hld.model_dump_json()}\n\nLLD:\n{lld.model_dump_json()}"
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_content)],
        config={"callbacks": [meter]}
    )