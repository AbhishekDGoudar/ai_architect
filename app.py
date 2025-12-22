import streamlit as st
import time
import json
from dotenv import load_dotenv
import streamlit.components.v1 as components

# Import our custom modules
from graph import app_graph
from storage import save_snapshot, list_snapshots, load_snapshot, delete_snapshot
# Import the detailed schemas
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Architect Studio",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""
if "current_result" not in st.session_state:
    st.session_state["current_result"] = None

# ==============================================================================
# 🛠️ HELPER FUNCTIONS
# ==============================================================================

def calculate_estimate(prompt_text, provider):
    """
    Rough calculation of token usage for the full 22-point framework + diagrams.
    """
    input_tokens = len(prompt_text) / 4 
    
    # System Overhead (Manager, Security, Lead, Judge + Massive Schemas)
    system_overhead = 4500 
    
    # Output Prediction (Verbose designs + Mermaid Code)
    estimated_output = 4000 
    
    total_est = input_tokens + system_overhead + estimated_output
    
    rates = {
        "openai": 10.00,  # Blended GPT-4o
        "gemini": 3.50,   # Gemini 1.5 Pro
        "claude": 15.00,  # Sonnet 3.5
        "ollama": 0.00    
    }
    cost = (total_est / 1_000_000) * rates.get(provider, 0)
    
    return int(total_est), cost

def render_mermaid(code: str, height=400, key=None):
    """
    Renders Mermaid code safely. Swallows errors to prevent UI crashes 
    if the LLM generates invalid syntax.
    """
    if not code:
        return

    # 1. Clean Markdown syntax (LLMs often wrap in ```mermaid ... ```)
    clean_code = code.replace("```mermaid", "").replace("```", "").strip()
    
    # 2. Basic Validation: Check for known Mermaid diagram types
    valid_starts = ["graph", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram", "C4Context"]
    if not any(clean_code.startswith(start) for start in valid_starts):
        st.caption("⚠️ Diagram code invalid or not generated.")
        return

    # 3. HTML Injection for Rendering via CDN
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        </script>
        <div class="mermaid">
            {clean_code}
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=height, scrolling=True)

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("⚙️ Configuration")
    
    st.subheader("AI Provider")
    provider = st.selectbox(
        "Select Model Backend",
        ("openai", "gemini", "claude", "ollama"),
        index=1,
        help="Gemini 1.5 Pro is recommended for large context windows."
    )
    
    if provider != "ollama":
        api_key_input = st.text_input(
            f"{provider.title()} API Key",
            type="password",
            value=st.session_state["api_key"],
            help="This key is used for this session only."
        )
        st.session_state["api_key"] = api_key_input
    else:
        st.info("Using Local Ollama (No Key Required)")
        st.session_state["api_key"] = "local"

    st.divider()

    st.subheader("📂 Snapshot Manager")
    snapshots = list_snapshots()
    
    selected_file = st.selectbox(
        "Saved Architectures:", 
        options=["(New Run)"] + snapshots,
        index=0
    )
    
    if selected_file != "(New Run)":
        col_load, col_del = st.columns(2)
        
        if col_load.button("📂 Load"):
            try:
                data = load_snapshot(selected_file)
                # Rehydrate Pydantic models from JSON dictionaries
                st.session_state["current_result"] = {
                    "hld": HighLevelDesign(**data['hld']),
                    "lld": LowLevelDesign(**data['lld']),
                    "verdict": JudgeVerdict(**data['verdict']),
                    "metrics": data.get("metrics", {}),
                    "logs": data.get("logs", [])
                }
                st.toast(f"Loaded '{selected_file}'", icon="✅")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Corrupt file or Schema mismatch: {e}")

        if col_del.button("🗑️ Delete"):
            success = delete_snapshot(selected_file)
            if success:
                st.toast(f"Deleted {selected_file}", icon="🗑️")
                time.sleep(1.0)
                st.rerun()
            else:
                st.error("Could not delete file.")

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================
st.title("🤖 AI Systems Architect")
st.markdown("Automated generation of **Enterprise-Grade** design documents covering **22 architectural points**.")

# ------------------------------------------------------------------------------
# CASE A: INPUT FORM (No Result Loaded)
# ------------------------------------------------------------------------------
if st.session_state["current_result"] is None:
    
    st.info("👋 Welcome! Describe the system you want to build below.")
    
    user_prompt = st.text_area(
        "System Requirements:", 
        height=200, 
        placeholder="Example: Build a scalable ride-sharing backend like Uber for 50k daily users. Must use SQL.",
        value="Build a scalable URL shortener like Bitly."
    )

    if user_prompt:
        est_tokens, est_cost = calculate_estimate(user_prompt, provider)
        with st.expander("📊 Cost & Token Estimate", expanded=False):
            c1, c2 = st.columns(2)
            c1.metric("Est. Tokens", f"~{est_tokens}")
            c2.metric("Est. Cost", f"${est_cost:.4f}")
            st.caption("Includes Security hardening and Quality Audit steps.")

    run_btn = st.button("🚀 Generate Architecture", type="primary", use_container_width=True)

    if run_btn:
        if not st.session_state["api_key"]:
            st.error(f"❌ Please enter an API Key for {provider.title()} in the sidebar.")
            st.stop()

        with st.status(f"Running Architect Pipeline on {provider.title()}...", expanded=True) as status:
            
            inputs = {
                "user_request": user_prompt, 
                "provider": provider,
                "api_key": st.session_state["api_key"],
                "retry_count": 0,
                "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
                "logs": []
            }
            
            try:
                final_state = app_graph.invoke(inputs)
                
                status.update(label="✅ Architecture Generated!", state="complete", expanded=False)
                
                st.session_state["current_result"] = {
                    "hld": final_state['hld'],
                    "lld": final_state['lld'],
                    "verdict": final_state['verdict'],
                    "metrics": {
                        "total": final_state['total_tokens'],
                        "prompt": 0, # Simplified for display
                        "completion": 0
                    },
                    "logs": final_state['logs']
                }
                st.rerun()

            except Exception as e:
                st.error(f"Execution Failed: {str(e)}")
                st.error("Please check your API Key and connection.")

# ------------------------------------------------------------------------------
# CASE B: RESULTS DISPLAY (Result Loaded)
# ------------------------------------------------------------------------------
else:
    res = st.session_state["current_result"]
    hld = res['hld']
    lld = res['lld']
    verdict = res['verdict']
    metrics = res['metrics']
    logs = res['logs']

    # --- Toolbar ---
    col_back, col_save, col_spacer = st.columns([1, 1, 4])
    if col_back.button("⬅️ Start New Run"):
        st.session_state["current_result"] = None
        st.rerun()
        
    if col_save.button("💾 Save Snapshot"):
        filename = save_snapshot("Run", {
            "user_request": "Snapshot", 
            "hld": hld.model_dump(), "lld": lld.model_dump(), "verdict": verdict.model_dump(),
            "metrics": metrics, "logs": logs
        })
        st.toast(f"Saved to {filename}", icon="✅")

    st.divider()

    # --- Metrics & Logs ---
    with st.expander("📈 Execution Metrics & Logs", expanded=False):
        st.metric("Total Tokens Used", metrics.get("total", 0))
        st.markdown("### Execution Trace")
        for log in logs:
            st.text(f"[{log.get('time', '')}] {log.get('role', 'System')}: {log.get('message', '')}")

    # --- TABS FOR HLD / LLD ---
    tab_hld, tab_lld = st.tabs(["🏛️ High Level Design (HLD)", "💻 Low Level Design (LLD)"])

    # ==========================================
    # HLD VISUALIZATION
    # ==========================================
    with tab_hld:
        st.title("High Level Design (Points 1-11)")
        
        # 1. Business Context
        with st.container(border=True):
            st.header("1. Business Context")
            st.markdown(f"**Problem:** {hld.business_context.problem_statement}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Goals & Metrics**")
                for item in hld.business_context.business_goals: st.success(f"- {item}")
                st.markdown("**In-Scope**")
                for item in hld.business_context.in_scope: st.info(f"- {item}")
            with c2:
                st.markdown("**Assumptions & Constraints**")
                for item in hld.business_context.assumptions_constraints: st.warning(f"- {item}")
                st.markdown("**Out-of-Scope / Non-Goals**")
                for item in hld.business_context.out_of_scope: st.error(f"- {item}")

        # 2. Architecture Overview
        with st.container(border=True):
            st.header("2. Architecture Overview")
            
            # Text Descriptions (Always safe to render)
            st.markdown(f"**Style:** `{hld.architecture_overview.style}`")
            st.markdown(f"**Context Desc:** {hld.architecture_overview.system_context_diagram_desc}")
            st.markdown(f"**Data Flow Desc:** {hld.architecture_overview.data_flow_desc}")

            # Diagrams (Render if valid)
            if hld.diagrams:
                st.divider()
                st.subheader("📐 Architecture Diagrams")
                t_ctx, t_cont, t_seq = st.tabs(["System Context", "Containers", "Data Flow"])
                
                with t_ctx:
                    render_mermaid(hld.diagrams.system_context, height=500)
                with t_cont:
                    render_mermaid(hld.diagrams.container_diagram, height=500)
                with t_seq:
                    render_mermaid(hld.diagrams.data_flow, height=600)
            else:
                st.caption("No diagrams generated for this run.")

        # 3. Core Components
        st.header("3. Core Components")
        cols = st.columns(len(hld.core_components) if len(hld.core_components) < 4 else 3)
        for idx, comp in enumerate(hld.core_components):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(comp.name)
                    st.write(comp.responsibility)
                    st.caption(f"Protocols: {', '.join(comp.communication_protocols)}")
                    st.caption(f"Boundaries: {comp.trust_boundaries}")

        # 4 & 5. Data & Integration
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.header("4. Data Architecture")
                st.markdown(f"**Consistency:** `{hld.data_architecture.consistency_model}`")
                st.markdown("**Storage Choices:**")
                st.json(hld.data_architecture.storage_choices)
                st.markdown(f"**Retention:** {hld.data_architecture.retention_archival_policy}")
        with c2:
            with st.container(border=True):
                st.header("5. Integration & APIs")
                st.markdown(f"**Contract:** `{hld.integration_strategy.contract_strategy}`")
                st.markdown("**Public APIs:**")
                for api in hld.integration_strategy.public_apis: st.code(api, language="text")

        # 6, 7, 8. NFRs & Security
        with st.expander("6-8. NFRs, Security, Reliability (Click to Expand)", expanded=True):
            t1, t2, t3 = st.tabs(["NFRs", "Security (Hardened)", "Reliability"])
            with t1:
                st.markdown(f"**Scalability:** {hld.nfrs.scalability_plan}")
                st.markdown(f"**Availability:** {hld.nfrs.availability_slo}")
                st.markdown(f"**Latency:** {hld.nfrs.latency_targets}")
            with t2:
                sec = hld.security_compliance
                st.warning(f"**Threat Model:** {sec.threat_model_summary}")
                st.markdown(f"**AuthN/AuthZ:** {sec.authentication_strategy} / {sec.authorization_strategy}")
                st.markdown(f"**Compliance:** {', '.join(sec.compliance_standards)}")
            with t3:
                rel = hld.reliability_resilience
                st.markdown(f"**Failure Modes:** {', '.join(rel.failure_modes)}")
                st.markdown(f"**DR (RPO/RTO):** {rel.disaster_recovery_rpo_rto}")

        # 11. Design Decisions
        st.header("11. Key Design Decisions")
        dec = hld.design_decisions
        st.info(f"**Tech Stack Justification:** {dec.tech_stack_justification}")
        st.error(f"**Rejected Alternatives:** {', '.join(dec.rejected_alternatives)}")
        st.success(f"**Patterns Used:** {', '.join(dec.patterns_used)}")

    # ==========================================
    # LLD VISUALIZATION
    # ==========================================
    with tab_lld:
        # Score Header
        score_color = "green" if verdict.is_valid else "red"
        st.markdown(f"### 🛡️ Architect's Verdict: :{score_color}[{verdict.score}/10]")
        if not verdict.is_valid:
            st.error(f"**Critique:** {verdict.critique}")
        else:
            st.success("Design Approved for Implementation.")
            
        st.divider()
        st.title("Low Level Design (Points 12-22)")

        # 12. Detailed Components
        st.subheader("12. Component Internal Design")
        for dcomp in lld.detailed_components:
            with st.expander(f"📦 {dcomp.component_name}", expanded=False):
                st.markdown("**Class Structure:**")
                st.code(dcomp.class_structure_desc, language="text")
                st.markdown(f"**Module Boundaries:** {dcomp.module_boundaries}")

        # 13 & 14. API & Data Deep Dive
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("13. API Specification")
            for api in lld.api_design:
                with st.expander(f"{api.method} {api.endpoint}"):
                    st.markdown(f"**Req:** `{api.request_schema}`")
                    st.markdown(f"**Res:** `{api.response_schema}`")
                    st.caption(f"Errors: {api.error_codes}")
        with c2:
            st.subheader("14. Data Model (Schema)")
            for model in lld.data_model_deep_dive:
                with st.container(border=True):
                    st.markdown(f"**Entity: {model.entity}**")
                    st.markdown(f"- Attributes: {model.attributes}")
                    st.markdown(f"- Indexes: `{model.indexes}`")

        # 15-22 Implementation Details
        st.divider()
        st.subheader("Implementation Strategy")
        
        t1, t2, t3, t4 = st.tabs(["Logic & Concurrency", "Security Impl", "Testing & Ops", "Governance"])
        
        with t1:
            st.markdown(f"**Core Algorithms:**\n{lld.business_logic.core_algorithms}")
            st.markdown(f"**Concurrency Control:**\n{lld.business_logic.concurrency_control}")
            st.markdown(f"**Error Handling:**\n{lld.error_handling.error_taxonomy}")
        
        with t2:
            st.subheader("Authentication Flow")
            # Render LLD Diagram safely
            render_mermaid(lld.security_implementation.auth_flow_diagram_desc)
            
            st.markdown(f"**Input Validation:**\n{lld.security_implementation.input_validation_rules}")
            st.markdown(f"**Token Lifecycle:** {lld.security_implementation.token_lifecycle}")
        
        with t3:
            st.markdown("**Testing Strategy:**")
            st.write(f"- Unit: {lld.testing_strategy.unit_test_scope}")
            st.write(f"- Integration: {lld.testing_strategy.integration_test_scope}")
            st.markdown("**Operational Readiness:**")
            st.write(f"- Runbooks: {lld.operational_readiness.runbook_summary}")
            st.write(f"- Rollback: {lld.operational_readiness.rollback_strategy}")

        with t4:
            st.write(f"**Code Docs:** {lld.documentation_governance.code_docs_standard}")
            st.write(f"**ADR Process:** {lld.documentation_governance.adr_process}")