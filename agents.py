from langchain_core.language_models import BaseChatModel
from typing import List, Optional
from datetime import date

from schemas import (
    HighLevelDesign, LowLevelDesign, JudgeVerdict, 
    SecurityCompliance, ArchitectureDiagrams, 
    RefinedDesign, DiagramValidationResult,
    ProjectStructure
)
from callbacks import TokenMeter
from rag import knowledge as kb 

# ==========================================
# AGENTS
# ==========================================

def engineering_manager(user_request: str, llm: BaseChatModel, meter: TokenMeter, feedback: str = ""):
    """Generates a fully populated High-Level Design (HLD). Diagrams remain null."""
    try:
        context = kb.search(user_request, use_web=True, use_kb=True)
    except Exception:
        context = "No knowledge base context available."
    
    today = date.today().isoformat()
    system_msg = f"""
You are a Principal Software Architect. 
Generate a fully populated High-Level Design (HLD) covering all fields.
CRITICAL: Leave 'diagrams' as null.

RULES:
1. Every field in the schema is REQUIRED except 'diagrams'.
2. Do NOT provide null or empty strings. Use "N/A" for text, [] for lists if empty.
3. Tech stack should include at least two layers.
4. Storage choices must be fully populated.
5. Citations are mandatory.
IMPORTANT: Consider the current date {today} and provide recommendations using the most relevant modern technologies available today.

CONTEXT:
{context}
"""
    
    if feedback:
        system_msg += f"\n\n⚠️ PREVIOUS FEEDBACK: {feedback}\nEnsure these issues are resolved."

    structured_llm = llm.with_structured_output(HighLevelDesign)
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_request)],
        config={"callbacks": [meter]}
    )


def security_specialist(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Refines the Security Compliance section."""
    hld_context = hld.model_dump_json(indent=2)
    today = date.today().isoformat()
    system_msg = f"""
You are a Security Specialist.
Review and harden the 'security_compliance' section.
Enforce GDPR, SOC2, and Zero Trust principles.
RETURN a fully populated SecurityCompliance object.
IMPORTANT: Consider the current date {today} and provide security best practices relevant today.

CURRENT HLD:
{hld_context}
"""
    
    structured_llm = llm.with_structured_output(SecurityCompliance)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Harden security strategy.")],
        config={"callbacks": [meter]}
    )


def team_lead(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Generates a fully populated Low-Level Design (LLD)."""
    hld_context = hld.model_dump_json(indent=2)
    today = date.today().isoformat()
    system_msg = f"""
You are a Senior Team Lead.
Generate the Low-Level Design (LLD) based on the HLD.

RULES:
1. Fill EVERY field. Use "N/A" for text or [] for lists if empty.
2. Focus on API Contracts, Data Models, and Component Internals.
3. Include citations for technical choices.
IMPORTANT: Consider the current date {today} and provide modern tech stack recommendations.

HLD CONTEXT:
{hld_context}
"""
    
    structured_llm = llm.with_structured_output(LowLevelDesign)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate detailed LLD.")],
        config={"callbacks": [meter]}
    )


def visual_architect(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Generates diagram Python code using the 'diagrams' library."""
    hld_summary = hld.model_dump_json(include={'core_components', 'architecture_overview', 'data_architecture'})
    today = date.today().isoformat()
    system_msg = f"""
You are a Visualization Expert.
Generate Python code using the 'diagrams' library for 3 diagrams: System Context, Container, Data Flow.

RULES:
- Include all HLD core components in diagrams.
- Use show=False in Diagram constructor.
- Return a valid ArchitectureDiagrams object with system_context, container_diagram, data_flow fields.
IMPORTANT: Consider the current date {today} and provide diagrams reflecting today’s architecture best practices.

CONTEXT:
{hld_summary}
"""
    
    structured_llm = llm.with_structured_output(ArchitectureDiagrams)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate diagram code.")],
        config={"callbacks": [meter]}
    )


def diagram_validator(hld: HighLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Validates the generated diagram code."""
    if not hld.diagrams:
        diagram_content = "No diagrams generated."
    else:
        diagram_content = "\n".join(
            f"System Context: {d.system_context}\nContainer: {d.container_diagram}\nData Flow: {d.data_flow}"
            for d in hld.diagrams
        )
    
    hld_components = [c.name for c in hld.core_components]
    today = date.today().isoformat()
    system_msg = f"""
You are a Diagram QA Expert. 
1. Check Python syntax for 'diagrams' library code.
2. Ensure all HLD core components are represented: {hld_components}.
IMPORTANT: Consider the current date {today} when validating diagrams.
"""
    
    structured_llm = llm.with_structured_output(DiagramValidationResult)
    return structured_llm.invoke(
        [("system", system_msg), ("human", diagram_content)],
        config={"callbacks": [meter]}
    )


def scaffold_architect(lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Generates project structure & starter files on-demand."""
    tech_stack_context = [c.component_name for c in lld.detailed_components]
    api_context = [a.endpoint for a in lld.api_design]
    today = date.today().isoformat()
    
    system_msg = f"""
You are a DevOps Architect.
Generate a practical starter project structure based on the LLD.

RULES:
1. Include requirements.txt / package.json matching the tech stack.
2. README.md explaining how to run the project.
3. docker-compose.yml if databases are required.
4. Skeleton code for Main Entrypoint.
IMPORTANT: Consider the current date {today} and provide modern setup recommendations.

COMPONENTS: {tech_stack_context}
API ENDPOINTS: {api_context}
"""
    
    structured_llm = llm.with_structured_output(ProjectStructure)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Generate project scaffolding.")],
        config={"callbacks": [meter]}
    )


def architecture_judge(hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Evaluates consistency between HLD and LLD."""
    today = date.today().isoformat()
    system_msg = f"""
You are a QA Architect. Evaluate HLD & LLD for consistency.
All list fields must be returned; return [] if empty.

CRITIQUE FOCUS:
- LLD components match HLD core components
- Technology stack consistency
IMPORTANT: Consider the current date {today} when evaluating.

"""
    
    structured_llm = llm.with_structured_output(JudgeVerdict)
    user_content = f"HLD:\n{hld.model_dump_json()}\n\nLLD:\n{lld.model_dump_json()}"
    
    return structured_llm.invoke(
        [("system", system_msg), ("human", user_content)],
        config={"callbacks": [meter]}
    )


def reiteration_agent(judge: JudgeVerdict, hld: HighLevelDesign, lld: LowLevelDesign, llm: BaseChatModel, meter: TokenMeter):
    """Refines both HLD and LLD based on Judge's critique."""
    today = date.today().isoformat()
    system_msg = f"""
You are a Principal Software Architect.
IMPROVE the full HLD and LLD based on critique.
Keep 'diagrams' as null in HLD.

CRITIQUE: {judge.critique}
HLD-LLD MISMATCHES: {judge.hld_lld_mismatch}
SECURITY GAPS: {judge.security_gaps}
IMPORTANT: Consider the current date {today} when updating designs.
"""
    
    structured_llm = llm.with_structured_output(RefinedDesign)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Refine the complete design iteratively.")],
        config={"callbacks": [meter]}
    )


def diagram_fixer(code: str, error_msg: str, llm: BaseChatModel, meter: TokenMeter):
    """Fixes broken diagram code and returns valid ArchitectureDiagrams."""
    today = date.today().isoformat()
    system_msg = f"""
You are a Python Expert specializing in 'diagrams' library.
Fix the following code:

ERROR: {error_msg}
BROKEN CODE: {code}

RULES:
- Return ONLY valid, corrected Python code.
- Ensure system_context, container_diagram, and data_flow fields are filled.
IMPORTANT: Consider the current date {today} when fixing the code.
"""
    
    structured_llm = llm.with_structured_output(ArchitectureDiagrams)
    return structured_llm.invoke(
        [("system", system_msg), ("human", "Fix this code.")],
        config={"callbacks": [meter]}
    )
# ==========================================