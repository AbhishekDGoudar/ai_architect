from langchain_core.language_models import BaseChatModel
from schemas import (HighLevelDesign, LowLevelDesign, JudgeVerdict, 
                     SecurityCompliance, ScaffoldingSpec, DiagramCode)
from callbacks import TokenMeter
from rag import kb

def engineering_manager(user_request: str, llm: BaseChatModel, meter: TokenMeter, feedback: str = ""):
    # 1. RAG Lookup
    context = kb.search(user_request)
    
    system_msg = f"""
    You are a Principal Software Architect. 
    Design a robust High Level Design (HLD) covering points 1 to 11.
    
    RELEVANT KNOWLEDGE BASE:
    {context}
    
    INSTRUCTIONS:
    - Fill the 'architecture_overview' with clear descriptions.
    - Prioritize Scalability, Security, and Cost.
    - Strictly adhere to the schema.
    """
    
    if feedback:
        system_msg += f"\n\nPREVIOUS REJECTION FEEDBACK: {feedback}\nFix the design."

    structured_llm = llm.with_structured_output(HighLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_request)],
        config={"callbacks": [meter]}
    )

def security_specialist(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    hld_context = hld.model_dump_json(indent=2)
    system_msg = f"""
    You are a Security Specialist (InfoSec).
    Review the 'security_compliance' section of the HLD.
    Refine it to meet strict standards (GDPR, SOC2, Zero Trust).
    
    CURRENT HLD:
    {hld_context}
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
    Generate the Low Level Design (LLD) covering points 12 to 22.
    Focus on Internal Class Design, API Contracts, and Data Models.
    
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
    Mark is_valid=False if:
    1. Components in LLD do not match HLD.
    2. Security requirements are ignored in implementation.
    """
    structured_llm = llm.with_structured_output(JudgeVerdict)
    
    user_content = f"HLD:\n{hld.model_dump_json()}\n\nLLD:\n{lld.model_dump_json()}"
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_content)],
        config={"callbacks": [meter]}
    )

def visual_architect(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    hld_summary = hld.model_dump_json(include={'core_components', 'data_architecture'})
    system_msg = f"""
    You are a Visualization Expert.
    Generate PYTHON CODE using the 'diagrams' library to visualize this architecture.
    
    RULES:
    1. Import 'Diagram' from 'diagrams'.
    2. Import nodes from 'diagrams.aws', 'diagrams.gcp', or 'diagrams.onprem' etc.
    3. Use `with Diagram("architecture_diagram", show=False):`
    4. Define nodes and edges (e.g. `web >> db`).
    5. Return ONLY valid Python code.
    
    CONTEXT:
    {hld_summary}
    """
    structured_llm = llm.with_structured_output(DiagramCode)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate diagram code.")],
        config={"callbacks": [meter]}
    )

def scaffold_architect(hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    hld_summary = hld.model_dump_json(include={'business_context', 'design_decisions'})
    lld_summary = lld.model_dump_json(include={'detailed_components', 'api_design'})
    
    system_msg = f"""
    You are a DevOps Engineer.
    Based on the design, generate the FILE STRUCTURE and STARTER CODE.
    
    1. Suggest a 'cookiecutter_url' if a standard template fits (e.g., Django, React).
    2. Define folder structure.
    3. Create 'README.md', 'requirements.txt', and 'docker-compose.yml'.
    4. Create placeholder code files for components.
    
    HLD: {hld_summary}
    LLD: {lld_summary}
    """
    
    structured_llm = llm.with_structured_output(ScaffoldingSpec)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Scaffold this project.")],
        config={"callbacks": [meter]}
    )