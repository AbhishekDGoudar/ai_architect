from langchain_core.language_models import BaseChatModel
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict, SecurityCompliance
from callbacks import TokenMeter

def engineering_manager(user_request: str, llm: BaseChatModel, meter: TokenMeter, feedback: str = ""):
    system_msg = """
    You are a Principal Software Architect. 
    Design a robust High Level Design (HLD) covering points 1 to 11 of our standard framework.
    
    INSTRUCTIONS FOR DIAGRAMS (PlantUML):
    1. System Context: Use 'component' diagram syntax.
    2. Container Diagram: Use 'package' or 'node' syntax to show boundaries.
    3. Data Flow: Use 'sequence' diagram syntax.
    4. ALWAYS wrap code in @startuml and @enduml tags.
    
    INSTRUCTIONS FOR CONTENT:
    - Fill the 'architecture_overview' with clear TEXT descriptions.
    - Prioritize Scalability, Security, and Cost.
    """
    
    if feedback:
        system_msg += f"\n\n⚠️ PREVIOUS REJECTION FEEDBACK: {feedback}\nFix the design or diagrams."

    structured_llm = llm.with_structured_output(HighLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_request)],
        config={"callbacks": [meter]}
    )





# def engineering_manager(user_request: str, llm: BaseChatModel, meter: TokenMeter, feedback: str = ""):
#     system_msg = """
#     You are a Principal Software Architect. 
#     Design a robust High Level Design (HLD) covering points 1 to 11 of our standard framework.
    
#     INSTRUCTIONS FOR DIAGRAMS (Crucial):
#     You MUST generate valid Mermaid.js code for the 'diagrams' section.
#     1. System Context: Use 'graph TD'.
#     2. Container Diagram: Use 'graph TD' with 'subgraph' blocks to show boundaries.
#     3. Data Flow: Use 'sequenceDiagram' to show the flow between components.
    
#     INSTRUCTIONS FOR CONTENT:
#     - Fill the 'architecture_overview' with clear TEXT descriptions (do not put mermaid code there).
#     - Prioritize Scalability, Security, and Cost.
#     """
    
#     if feedback:
#         system_msg += f"\n\n⚠️ PREVIOUS REJECTION FEEDBACK: {feedback}\nFix the design or diagrams based on this feedback."

#     structured_llm = llm.with_structured_output(HighLevelDesign)
    
#     return structured_llm.invoke(
#         [("system", system_msg), ("human", user_request)],
#         config={"callbacks": [meter]}
#     )

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
    
    Focus on Internal Class Design, API Contracts, Data Models (Indexes/Constraints), and Failure Modes.
    
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
    
    CRITICAL DIAGRAM VERIFICATION (PlantUML):
    1. Check if 'diagrams' fields contain '@startuml' and '@enduml'.
    2. Verify the PlantUML syntax is logically valid.
    3. If any diagram is missing or invalid, mark is_valid=False.

    GENERAL CHECKS:
    1. LLD components match HLD components.
    2. Security implementation in LLD matches HLD compliance rules.
    """
    structured_llm = llm.with_structured_output(JudgeVerdict)
    
    user_content = f"HLD:\n{hld.model_dump_json()}\n\nLLD:\n{lld.model_dump_json()}"
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_content)],
        config={"callbacks": [meter]}
    )