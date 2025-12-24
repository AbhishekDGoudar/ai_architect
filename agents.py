from langchain_core.language_models import BaseChatModel
from typing import List, Optional

# Import the strictly required unified schemas
from schemas import (
    HighLevelDesign, LowLevelDesign, JudgeVerdict, 
    SecurityCompliance, ArchitectureDiagrams, 
    RefinedDesign, DiagramValidationResult,
    ProjectStructure
)
from callbacks import TokenMeter
# Import the knowledge engine
from rag import knowledge as kb 

# ==========================================
# 🤖 AGENTS
# ==========================================

def engineering_manager(user_request: str, llm: BaseChatModel, meter: TokenMeter, feedback: str = ""):
    """Generates the initial High-Level Design (HLD)."""
    try:
        context = kb.search(user_request, use_web=True, use_kb=True)
    except Exception:
        context = "No knowledge base context available."
    
    system_msg = f"""
    You are a Principal Software Architect. 
    Design a robust High Level Design (HLD) covering the 11-point framework.

    COMPLIANCE RULES:
    1. EVERY field in the schema is REQUIRED *EXCEPT* 'diagrams'.
    2. Do NOT provide null or empty strings. If a field doesn't apply, use "N/A".
    3. For 'tech_stack', provide a LIST of objects with 'layer' and 'technology'.
    4. For 'storage_choices', provide a LIST of objects with 'component' and 'technology'.
    5. 'citations' are MANDATORY. Use your internal knowledge for citations if web data is low.
    6. CRITICAL: Leave 'diagrams' as null. Do NOT generate URLs or placeholders. A separate specialist handles this.

    RELEVANT CONTEXT:
    {context}
    """
    
    if feedback:
        system_msg += f"\n\n⚠️ CRITICAL FEEDBACK FROM PREVIOUS RUN: {feedback}\nYou MUST address these issues in this iteration."

    structured_llm = llm.with_structured_output(HighLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_request)],
        config={"callbacks": [meter]}
    )

def security_specialist(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Refines the Security Compliance section of the HLD."""
    hld_context = hld.model_dump_json(indent=2)
    system_msg = f"""
    You are a Security Specialist. Review and harden the 'security_compliance' section.
    Enforce GDPR, SOC2, and Zero Trust principles.
    
    REQUIREMENT: You must return a fully populated SecurityCompliance object. 
    No optional fields are allowed.
    
    CURRENT HLD FOR REVIEW:
    {hld_context}
    """
    
    structured_llm = llm.with_structured_output(SecurityCompliance)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Harden security strategy.")],
        config={"callbacks": [meter]}
    )

def team_lead(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Generates the Low-Level Design (LLD)."""
    hld_context = hld.model_dump_json(indent=2)
    system_msg = f"""
    You are a Senior Team Lead. Generate the Low Level Design (LLD) based on the HLD.
    
    COMPLIANCE RULES:
    1. Fill EVERY field. Use "N/A" for text or [] for lists if no data exists.
    2. Focus on API Contracts, Data Models, and Component Internals.
    3. Ensure 'citations' are included for technical choices.
    
    HLD ARCHITECTURE TO IMPLEMENT: 
    {hld_context}
    """
    structured_llm = llm.with_structured_output(LowLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate detailed LLD.")],
        config={"callbacks": [meter]}
    )

def visual_architect(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Generates Python code for Architecture Diagrams."""
    hld_summary = hld.model_dump_json(include={'core_components', 'architecture_overview', 'data_architecture'})
    
    system_msg = f"""
    You are a Visualization Expert.
    Generate VALID PYTHON CODE using the 'diagrams' library for 3 distinct diagrams.

    DIAGRAMS REQUIRED:
    1. System Context: Show users and external systems.
    2. Container Diagram: Show services, databases, and queues.
    3. Data Flow: Show sensitive data paths and trust boundaries.

    CRITICAL CODING RULES:
    - Use standard imports (e.g., `from diagrams.aws.compute import EC2`).
    - ALWAYS include `show=False` in the Diagram constructor to prevent opening files.
      Example: `with Diagram("Name", show=False):`
    - Do NOT call `os.system` or file operations other than Diagram logic.
    - Return a valid 'ArchitectureDiagrams' object with all 3 code strings.
    
    CONTEXT:
    {hld_summary}
    """
    structured_llm = llm.with_structured_output(ArchitectureDiagrams)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate diagram code.")],
        config={"callbacks": [meter]}
    )

def architecture_judge(hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Evaluates consistency between HLD and LLD."""
    system_msg = """
    You are a QA Architect. Evaluate the HLD and LLD for consistency and gaps.
    
    STRICT REQUIREMENT: 
    Every list in the schema (e.g., security_gaps, diagram_issues) must be present. 
    If no issues are found for a category, return an empty list [].
    
    CRITIQUE FOCUS:
    - Are LLD components tracking HLD core components?
    - Is the technology stack consistent?
    """
    structured_llm = llm.with_structured_output(JudgeVerdict)
    
    user_content = f"HLD:\n{hld.model_dump_json()}\n\nLLD:\n{lld.model_dump_json()}"
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_content)],
        config={"callbacks": [meter]}
    )

def reiteration_agent(judge: JudgeVerdict, hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Refines the design based on the Judge's critique."""
    system_msg = f"""
    You are a Principal Software Architect.
    Review the Judge's critique and IMPROVE both the HLD and LLD.
    
    You must output a 'RefinedDesign' object containing the full updated HLD and LLD.
    Do not return partial updates; return the complete objects.
    
    IMPORTANT: Keep 'diagrams' as null in the HLD. Do not attempt to generate diagrams here.
    
    CRITIQUE: {judge.critique}
    MISMATCHES: {judge.hld_lld_mismatch}
    SECURITY GAPS: {judge.security_gaps}
    """
    structured_llm = llm.with_structured_output(RefinedDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Refine the complete design iteratively.")],
        config={"callbacks": [meter]}
    )

def diagram_validator(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Validates the generated diagram code."""
    if not hld.diagrams:
        diagram_content = "No diagrams were generated."
    else:
        diagram_content = f"""
        System Context Code: {hld.diagrams.system_context}
        Container Code: {hld.diagrams.container_diagram}
        """
    
    hld_components = [c.name for c in hld.core_components]
    
    system_msg = f"""
    You are a Diagram QA Expert. 
    1. Check for Python syntax errors in the 'diagrams' library code.
    2. Ensure these HLD components are present in the diagrams: {hld_components}.
    """
    
    structured_llm = llm.with_structured_output(DiagramValidationResult)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", diagram_content)],
        config={"callbacks": [meter]}
    )

def scaffold_architect(lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Generates the file structure and starter code on-demand."""
    
    # Extract context to keep tokens low
    tech_stack_context = [c.component_name for c in lld.detailed_components]
    api_context = [a.endpoint for a in lld.api_design]
    
    system_msg = f"""
    You are a DevOps Architect.
    Generate a practical starter project structure based on the Low Level Design.
    
    RULES:
    1. Generate a 'requirements.txt' or 'package.json' matching the tech stack.
    2. Create a 'README.md' explaining how to run the project.
    3. Generate 'docker-compose.yml' if databases are required.
    4. Generate skeleton code for the Main Entrypoint (e.g., main.py or index.js).
    
    COMPONENTS TO SCAFFOLD: {tech_stack_context}
    API ENDPOINTS: {api_context}
    """
    
    structured_llm = llm.with_structured_output(ProjectStructure)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate project scaffolding.")],
        config={"callbacks": [meter]}
    )