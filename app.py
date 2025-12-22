import streamlit as st
import time
import json
import zlib
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Import our custom modules
from graph import app_graph
from storage import save_snapshot, list_snapshots, load_snapshot, delete_snapshot, check_snapshot_exists
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
if "project_name" not in st.session_state:
    st.session_state["project_name"] = ""

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
    
    # Output Prediction (Verbose designs + PlantUML Code)
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

# --- Diagram Rendering Logic (Hybrid) ---

def base64_encode_plantuml(input_bytes):
    """
    Custom Base64 encoding for PlantUML (No padding, specific charset).
    Maps 3 bytes to 4 characters from the custom PlantUML alphabet.
    """
    _b64_str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    res = ""
    i = 0
    while i < len(input_bytes):
        b1 = input_bytes[i]
        b2 = input_bytes[i+1] if i+1 < len(input_bytes) else 0
        b3 = input_bytes[i+2] if i+2 < len(input_bytes) else 0
        
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        
        res += _b64_str[c1] + _b64_str[c2]
        if i+1 < len(input_bytes): res += _b64_str[c3]
        if i+2 < len(input_bytes): res += _b64_str[c4]
        i += 3
    return res

def render_plantuml(code: str, caption: str):
    """Encodes and renders PlantUML via official server."""
    try:
        # Auto-fix: Ensure tags exist if missing
        if "@startuml" not in code:
            code = f"@startuml\n{code}\n@enduml"
            
        zlibbed = zlib.compress(code.encode('utf-8'))
        compressed = zlibbed[2:-4] # Strip headers/checksum
        encoded = base64_encode_plantuml(compressed)
        url = f"http://www.plantuml.com/plantuml/svg/{encoded}"
        st.image(url, caption=caption, use_container_width=True)
    except Exception as e:
        st.error(f"PlantUML Error: {e}")
        st.code(code, language="text")

def render_mermaid(code: str, height=400):
    """Renders Mermaid.js via HTML injection."""
    clean_code = code.replace("```mermaid", "").replace("```", "").strip()
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
        </script>
        <div class="mermaid">
            {clean_code}
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=height, scrolling=True)

def render_diagram(code: str, caption: str = "Diagram"):
    """
    HYBRID RENDERER: Detects format (PlantUML vs Mermaid) and renders appropriately.
    """
    if not code: return

    # 1. Detect PlantUML indicators
    if "@startuml" in code or "package " in code or "node " in code or "component " in code:
        render_plantuml(code, caption)
        
    # 2. Detect Mermaid indicators
    elif any(x in code for x in ["graph TD", "sequenceDiagram", "classDiagram", "C4Context"]):
        render_mermaid(code)
        
    # 3. Fallback / Ambiguous
    else:
        # Try PlantUML as default if it looks like structured code
        if "{" in code and "}" in code:
             render_plantuml(code, caption)
        else:
             st.code(code, language="text")

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
                # Load project name from file or filename
                st.session_state["project_name"] = data.get("project_name", selected_file.replace(".json", ""))
                
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
    
    st.info("👋 Welcome! Define your project below.")
    
    # 1. Project Name Input
    project_name = st.text_input(
        "Project Name", 
        value=st.session_state.get("project_name", ""),
        placeholder="e.g., Enterprise URL Shortener",
        help="This will be used as the filename for saving."
    )
    st.session_state["project_name"] = project_name
    
    # 2. Requirements Input
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
        # Validation
        if not st.session_state["api_key"]:
            st.error(f"❌ Please enter an API Key for {provider.title()} in the sidebar.")
            st.stop()
            
        if not project_name.strip():
            st.error("❌ Please provide a Project Name.")
            st.stop()

        # Check if file exists to prevent accidental overwrites
        if check_snapshot_exists(project_name):
            st.error(f"⚠️ A project named '{project_name}' already exists! Please choose a different name or delete the existing one.")
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
                        "prompt": 0, # Simplified
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
        st.session_state["project_name"] = ""
        st.rerun()
        
    if col_save.button("💾 Save Project"):
        p_name = st.session_state.get("project_name", "Untitled")
        filename = save_snapshot(p_name, {
            "user_request": "Snapshot", 
            "hld": hld.model_dump(), "lld": lld.model_dump(), "verdict": verdict.model_dump(),
            "metrics": metrics, "logs": logs
        })
        st.toast(f"Saved project to {filename}", icon="✅")

    st.divider()
    st.subheader(f"Project: {st.session_state.get('project_name', 'Untitled')}")

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
            st.markdown(f"**Style:** `{hld.architecture_overview.style}`")
            
            # Text Descriptions
            st.markdown(f"**Context:** {hld.architecture_overview.system_context_diagram_desc}")
            st.markdown(f"**Data Flow:** {hld.architecture_overview.data_flow_desc}")
            st.markdown(f"**Dependencies:** {', '.join(hld.architecture_overview.external_dependencies)}")

            # 🛠️ HYBRID RENDERING (PlantUML / Mermaid)
            if hld.diagrams:
                st.divider()
                st.subheader("📐 Architecture Diagrams")
                t_ctx, t_cont, t_seq = st.tabs(["System Context", "Containers", "Data Flow"])
                
                with t_ctx:
                    render_diagram(hld.diagrams.system_context, "System Context")
                with t_cont:
                    render_diagram(hld.diagrams.container_diagram, "Container Diagram")
                with t_seq:
                    render_diagram(hld.diagrams.data_flow, "Data Flow Sequence")
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
            
            # Hybrid Rendering for Security Flow
            render_diagram(lld.security_implementation.auth_flow_diagram_desc, "Auth Flow")
                
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