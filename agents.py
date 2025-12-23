from langchain_core.language_models import BaseChatModel
from schemas import (HighLevelDesign, LowLevelDesign, JudgeVerdict, 
                     SecurityCompliance, ScaffoldingSpec, ArchitectureDiagrams,
                     RefinedDesign, DiagramValidationResult)
from callbacks import TokenMeter
from rag import kb  # Assuming 'rag' module exists and has the `kb` object
from typing import List, Optional, Dict, Literal, Any

def engineering_manager(user_request: str, llm: BaseChatModel, meter: TokenMeter, feedback: str = ""):
    """
    Engineering Manager Agent:
    - Handles the generation of High-Level Design (HLD).
    - Uses RAG lookup for additional knowledge.
    """
    try:
        context = kb.search(user_request)
    except Exception:
        context = "No knowledge base context available."
    
    system_msg = f"""
    You are a Principal Software Architect. 
    Design a robust High Level Design (HLD) covering points 1 to 11.

    **IMPORTANT**:
    - Ensure **documentation** for each section.
    - Provide **examples** for each component and step.
    - Each decision must be justified based on **reputable sources**.

    RELEVANT KNOWLEDGE BASE:
    {context}

    STYLE & TONE GUIDELINES:
    1. **Professional & Technical**: Avoid buzzwords.
    2. **Citations**: Cite reputable architecture books/papers.

    INSTRUCTIONS:
    - Fill 'business_context' (Version, Stakeholders, Change Log).
    - Ensure clear 'architecture_overview'.
    - Focus on Scalability, Security, and Cost.
    """
    
    if feedback:
        system_msg += f"\n\n⚠️ PREVIOUS REJECTION FEEDBACK: {feedback}\nFix the design."

    structured_llm = llm.with_structured_output(HighLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_request)],
        config={"callbacks": [meter]}
    )

def security_specialist(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """
    Security Specialist Agent:
    - Reviews and refines the security compliance part of the HLD.
    """
    hld_context = hld.model_dump_json(indent=2)
    system_msg = f"""
    You are a Security Specialist (InfoSec).
    Review the 'security_compliance' section of the HLD.
    Refine it to meet strict standards (GDPR, SOC2, Zero Trust).

    **IMPORTANT**:
    - Enforce **GDPR** and **Zero Trust**.
    - Cite **NIST**, **ISO** standards.

    CURRENT HLD:
    {hld_context}
    """
    
    structured_llm = llm.with_structured_output(SecurityCompliance)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Harden this security design.")],
        config={"callbacks": [meter]}
    )

def team_lead(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """
    Team Lead Agent:
    - Generates Low-Level Design (LLD) from HLD.
    """
    hld_context = hld.model_dump_json(indent=2)
    system_msg = f"""
    You are a Senior Team Lead. 
    Generate Low Level Design (LLD) (Points 12-22).
    Focus on **Class Design**, **API Contracts**, and **Data Models**.

    **IMPORTANT**:
    - **Versioning** of components.
    - **Error Handling** details.
    - **Integration** specifics.

    ARCHITECT'S DESIGN: 
    {hld_context}
    """
    structured_llm = llm.with_structured_output(LowLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate LLD")],
        config={"callbacks": [meter]}
    )

def visual_architect(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """
    Visual Architect Agent:
    - Generates the Python code for diagrams using the 'diagrams' library.
    """
    hld_summary = hld.model_dump_json(include={'core_components', 'architecture_overview'})
    
    system_msg = f"""
    You are a Visualization Expert.
    Generate VALID PYTHON CODE using the 'diagrams' library for 3 diagrams:
    1. System Context
    2. Container Diagram
    3. Data Flow

    STRICT RULES:
    1. **No Pseudo-code**: Use valid classes (e.g. `from diagrams.aws.compute import EC2`).
    2. **Context Managers**: Use `with Diagram("Name", show=False):` for each.
    3. **Output**: Return strings containing the executable python code.

    CONTEXT:
    {hld_summary}
    """
    structured_llm = llm.with_structured_output(ArchitectureDiagrams)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate diagram code.")],
        config={"callbacks": [meter]}
    )

def architecture_judge(hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """
    Architecture Judge Agent (Iteration-aware).
    """
    system_msg = """
    You are a QA Architect. Evaluate HLD and LLD.
    
    CATEGORIES TO CHECK:
    1. HLD ↔ LLD consistency
    2. Security gaps
    3. NFR mismatches
    4. Diagram consistency
    5. Testing coverage

    OUTPUT: JudgeVerdict object.
    """
    structured_llm = llm.with_structured_output(JudgeVerdict)
    
    user_content = f"HLD:\n{hld.model_dump_json()}\n\nLLD:\n{lld.model_dump_json()}"
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_content)],
        config={"callbacks": [meter]}
    )

def reiteration_agent(judge: JudgeVerdict, hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """
    Automatically refines HLD and LLD based on JudgeVerdict recommendations.
    """
    system_msg = f"""
    You are a Principal Software Architect.
    Review the Judge's critique and IMPROVE the HLD and LLD.

    CRITIQUE: {judge.critique}
    ISSUES: {judge.hld_lld_mismatch}, {judge.security_gaps}, {judge.nfr_mismatches}

    Return a `RefinedDesign` object containing the full updated HLD and LLD.
    """
    # Use the wrapper class defined at the top
    structured_llm = llm.with_structured_output(RefinedDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Refine designs iteratively.")],
        config={"callbacks": [meter]}
    )

def diagram_validator(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """
    Validates syntax and consistency of diagram code.
    """
    if not hld.diagrams:
        diagram_code = "No diagrams found."
    else:
        diagram_code = f"""
        System Context: {hld.diagrams.system_context}
        Container: {hld.diagrams.container_diagram}
        Data Flow: {hld.diagrams.data_flow}
        """
    
    system_msg = f"""
    You are a Diagram QA Architect.
    1. Verify Python syntax for `diagrams` library.
    2. Ensure nodes match HLD components.
    3. Identify missing/invalid elements.
    """
    
    # Use wrapper class
    structured_llm = llm.with_structured_output(DiagramValidationResult)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", diagram_code)],
        config={"callbacks": [meter]}
    )

def scaffold_architect(hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """
    Scaffold Architect Agent.
    """
    hld_summary = hld.model_dump_json(include={'business_context', 'tech_stack'})
    lld_summary = lld.model_dump_json(include={'detailed_components', 'api_design'})
    
    system_msg = f"""
    You are a DevOps Engineer.
    Generate FILE STRUCTURE and STARTER CODE.

    1. Define folder structure.
    2. Create 'README.md', 'requirements.txt'.
    3. Create stub files.

    HLD: {hld_summary}
    LLD: {lld_summary}
    """
    
    structured_llm = llm.with_structured_output(ScaffoldingSpec)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Scaffold this project.")],
        config={"callbacks": [meter]}
    )