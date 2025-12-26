from langchain_core.language_models import BaseChatModel
from typing import List, Optional
import datetime
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

def visual_architect(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Generates Python code for Architecture Diagrams."""
    hld_summary = hld.model_dump_json(include={'core_components', 'architecture_overview', 'data_architecture'})
    today = datetime.date.today().isoformat()
    system_msg = f"""
    You are a Visualization Expert.
    Generate Mermaid.js code for 3 diagrams: System Context, Container, Data Flow.

    RULES:
    - Use standard Mermaid syntax (e.g. `graph TD`, `sequenceDiagram`).
    - Do NOT use Markdown backticks (```) in the output fields, just the raw code.
    - For System Context: Use `graph TD` showing external systems and user interacting with the main system.
    - For Container: Use `graph TD` with `subgraph` to group components.
    - For Data Flow: Use `sequenceDiagram` to show interaction steps.
    IMPORTANT: Consider the current date {today}.

    CONTEXT:
    {hld_summary}
    """
    structured_llm = llm.with_structured_output(ArchitectureDiagrams)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate diagram code.")],
        config={"callbacks": [meter]}
    )

def diagram_fixer(
    system_context_code: str, container_diagram_code: str, data_flow_code: str,
    system_context_error: str, container_diagram_error: str, data_flow_error: str,
    llm: BaseChatModel, meter: TokenMeter
) -> ArchitectureDiagrams:
    """
    Receives the Mermaid code and errors for all three diagrams,
    returns corrected versions for all diagrams in a single LLM call.
    """
    system_msg = f"""
    You are a Mermaid.js diagram expert.

    The following diagrams have syntax errors. Please correct the Mermaid.js code for each diagram:

    1. **System Context Diagram**:
    Error: {system_context_error}
    Original code:
    {system_context_code}

    2. **Container Diagram**:
    Error: {container_diagram_error}
    Original code:
    {container_diagram_code}

    3. **Data Flow Diagram**:
    Error: {data_flow_error}
    Original code:
    {data_flow_code}

    Please correct each Mermaid.js diagram code and return only valid code for each diagram.
    Do NOT change the logic or structure unnecessarily.
    """

    # Use LLM to fix all three diagrams in one call
    structured_llm = llm.with_structured_output(ArchitectureDiagrams)
    fixed_code = structured_llm.invoke(
        [("system", system_msg), ("human", "Fix the diagrams.")],
        config={"callbacks": [meter]}
    )

    return fixed_code



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