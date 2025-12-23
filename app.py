import streamlit as st
import pandas as pd
import os
import zipfile
import io
import time
from dotenv import load_dotenv

# Import your actual graph and schemas
from graph import app_graph
from schemas import (HighLevelDesign, LowLevelDesign, JudgeVerdict, 
                     DiagramCode, ScaffoldingSpec)
from storage import save_snapshot, list_snapshots, load_snapshot, delete_snapshot

load_dotenv()

# Define Knowledge Base Directory
KB_DIR = os.getenv("KB_DIR", "./knowledge_base")
if not os.path.exists(KB_DIR):
    os.makedirs(KB_DIR)

# --- Page Config ---
st.set_page_config(
    page_title="AI Architect Studio v2",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    h2 { border-bottom: 2px solid #ccc; padding-bottom: 10px; margin-top: 30px; }
    h3 { margin-top: 20px; color: #444; }
    h4 { margin-top: 15px; font-weight: bold; font-size: 1.05rem; }
    div[data-testid="stDataFrame"] { font-size: 0.9rem; }
    .report-list { margin-left: 20px; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if "api_key" not in st.session_state: st.session_state["api_key"] = ""
if "current_result" not in st.session_state: st.session_state["current_result"] = None
if "project_name" not in st.session_state: st.session_state["project_name"] = ""

# ==============================================================================
# 🛠️ DISPLAY HELPERS
# ==============================================================================

def calculate_estimate(prompt_text, provider):
    input_tokens = len(prompt_text) / 4 
    system_overhead = 6000 
    estimated_output = 5500 
    total_est = input_tokens + system_overhead + estimated_output
    rates = {
        "openai": 5.00, "gemini": 3.50, "claude": 15.00, "ollama": 0.00
    }
    cost = (total_est / 1_000_000) * rates.get(provider, 0)
    return int(total_est), cost

def render_bullets(data_list):
    if not data_list:
        st.caption("None defined.")
        return
    clean_list = "\n".join([f"- {item}" for item in data_list])
    st.markdown(clean_list)

def render_kv_table(data_dict, key_col="Item", val_col="Value"):
    if not data_dict:
        st.caption("No data.")
        return
    df = pd.DataFrame(list(data_dict.items()), columns=[key_col, val_col])
    st.table(df)

def create_zip_bytes(scaffold: ScaffoldingSpec) -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("project_structure.txt", scaffold.folder_structure)
        for file_spec in scaffold.starter_files:
            zip_file.writestr(file_spec.filename, file_spec.content)
    return zip_buffer.getvalue()

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("⚙️ Controls")
    
    # 1. Provider
    provider = st.selectbox("Backend", ["openai", "gemini", "claude", "ollama"], index=1)
    if provider == "ollama": 
        st.session_state["api_key"] = "local"
        st.info("Using Local Ollama")
    else: 
        st.session_state["api_key"] = st.text_input("API Key", type="password", value=st.session_state["api_key"])
    
    st.divider()

    # 2. Knowledge Base
    with st.expander("📚 Knowledge Base (RAG)", expanded=True):
        st.caption("Upload company standards (PDF/TXT).")
        uploaded_file = st.file_uploader("Add Document", type=["pdf", "txt"])
        
        if uploaded_file:
            # Save to persistent KB_DIR so it's there for future reloads
            save_path = os.path.join(KB_DIR, uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Saved: {uploaded_file.name}")
            
        if st.button("🔄 Ingest Documents", use_container_width=True):
            with st.spinner("Indexing Knowledge Base..."):
                try:
                    # Import the new engine
                    from rag import knowledge
                    
                    # 1. Ingest the persistent directory
                    msg = knowledge.ingest_directory()
                    
                    # 2. (Optional) If you want to ingest the specific upload immediately 
                    # without saving to disk first, you could use knowledge.ingest_upload(uploaded_file)
                    
                    st.toast(msg, icon="✅")
                    st.success(msg)
                except Exception as e:
                    st.error(f"Ingestion Failed: {e}")

    st.divider()

    # 3. Snapshots
    st.subheader("📂 Snapshots")
    if st.session_state["current_result"]:
        if st.button("💾 Save Current Project", use_container_width=True):
            p_name = st.session_state["project_name"] or "Untitled"
            save_snapshot(p_name, st.session_state["current_result"])
            st.toast(f"Project '{p_name}' saved!", icon="✅")
            time.sleep(1)
            st.rerun()
            
    snapshots = list_snapshots()
    selected_file = st.selectbox("Select Project:", ["(New Run)"] + snapshots)
    
    if selected_file != "(New Run)":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📂 Load", use_container_width=True):
                data = load_snapshot(selected_file)
                st.session_state["current_result"] = {
                    "hld": HighLevelDesign(**data['hld']) if data.get('hld') else None,
                    "lld": LowLevelDesign(**data['lld']) if data.get('lld') else None,
                    "verdict": JudgeVerdict(**data['verdict']) if data.get('verdict') else None,
                    "scaffold": ScaffoldingSpec(**data['scaffold']) if data.get('scaffold') else None,
                    "diagram_code": data.get("diagram_code"), 
                    "diagram_path": data.get("diagram_path"),
                    "metrics": data.get("metrics", {}),
                    "logs": data.get("logs", [])
                }
                st.session_state["project_name"] = data.get("project_name", "")
                st.rerun()
        with c2:
            if st.button("🗑️ Del", use_container_width=True):
                delete_snapshot(selected_file)
                st.toast(f"Deleted {selected_file}", icon="🗑️")
                time.sleep(1)
                st.rerun()
            
    st.divider()
    if st.button("⬅️ Clear Session", use_container_width=True):
        st.session_state["current_result"] = None
        st.session_state["project_name"] = ""
        st.rerun()

# ==============================================================================
# MAIN PAGE
# ==============================================================================
st.title("🤖 AI Architect Studio")

if st.session_state["current_result"] is None:
    # --- INPUT ---
    project_name = st.text_input("Project Name", value=st.session_state.get("project_name", ""))
    st.session_state["project_name"] = project_name
    user_prompt = st.text_area("System Requirements", height=200, placeholder="Describe the system...")
    
    if user_prompt:
        est_tokens, est_cost = calculate_estimate(user_prompt, provider)
        with st.container(border=True):
            st.markdown("#### 📊 Pre-Run Estimate")
            c1, c2, c3 = st.columns(3)
            c1.metric("Est. Tokens", f"~{est_tokens:,}")
            c2.metric("Est. Cost", f"${est_cost:.4f}")
            c3.caption("Includes RAG overhead, Diagrams, and Scaffolding.")

    if st.button("🚀 Generate Architecture", type="primary"):
        if not st.session_state["api_key"]: st.error("API Key required."); st.stop()
        if not project_name: st.error("Project Name required."); st.stop()
        
        with st.status("Architecting System...", expanded=True) as status:
            inputs = {"user_request": user_prompt, "provider": provider, "api_key": st.session_state["api_key"], "retry_count": 0, "total_tokens": 0, "logs": []}
            final_state = app_graph.invoke(inputs)
            st.session_state["current_result"] = final_state
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

else:
    # --- RESULTS ---
    res = st.session_state["current_result"]
    hld: HighLevelDesign = res.get('hld')
    lld: LowLevelDesign = res.get('lld')
    verdict: JudgeVerdict = res.get('verdict')
    scaffold: ScaffoldingSpec = res.get('scaffold')
    metrics = res.get('metrics', {})

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    security_score = metrics.get('security_score', 0) * 100
    m1.metric("Security Score", f"{security_score:.0f}%", delta=f"{security_score-80:.0f}%" if security_score>80 else f"{security_score-80:.0f}%")
    m2.metric("Tokens Used", f"{res.get('total_tokens', 0):,}")
    verdict_icon = '✅ Approved' if verdict.is_valid else '❌ Rejected'
    m3.metric("Verdict", verdict_icon)
    if m4.button("💾 Save Snapshot", key="main_save"):
        save_snapshot(st.session_state["project_name"] or "Untitled", res)
        st.toast("Snapshot saved!")

    tabs = st.tabs(["🏛️ High Level Design", "💻 Low Level Design", "📂 Artifacts & Code"])

    # ==========================================================================
    # TAB 1: HIGH LEVEL DESIGN (HLD) - ALL 11 SECTIONS
    # ==========================================================================
    with tabs[0]:
        st.header(f"High Level Design Document (v{hld.business_context.version})")
        
        # 1. Business Context
        st.subheader("1. Business Context")
        with st.container(border=True):
            st.markdown(f"**Problem:** {hld.business_context.problem_statement}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Goals:**")
                render_bullets(hld.business_context.business_goals)
            with c2:
                st.markdown("**Stakeholders:**")
                render_bullets(hld.business_context.stakeholders)
            st.divider()
            st.markdown("**Assumptions:**")
            render_bullets(hld.business_context.assumptions_constraints)

        # 2. Architecture Overview
        st.subheader("2. Architecture Overview")
        with st.container(border=True):
            st.markdown(f"**Style:** `{hld.architecture_overview.style}`")
            st.markdown(f"**Context:** {hld.architecture_overview.system_context_diagram_desc}")
            st.markdown("#### Tech Stack")
            render_kv_table(hld.architecture_overview.tech_stack)

        # 3. Core Components
        st.subheader("3. Core Components")
        for comp in hld.core_components:
            with st.expander(f"📦 {comp.name} ({comp.component_ownership})"):
                st.write(comp.responsibility)
                st.caption(f"Patterns: {', '.join(comp.design_patterns)}")
                st.markdown(f"**Boundaries:** {comp.trust_boundaries}")

        # 4. Data Architecture
        st.subheader("4. Data Architecture")
        with st.container(border=True):
            st.markdown(f"**Consistency:** `{hld.data_architecture.consistency_model}`")
            st.markdown(f"**Retention:** {hld.data_architecture.data_retention_policy}")
            st.markdown("**Storage Map:**")
            render_kv_table(hld.data_architecture.storage_choices)

        # 5. Integration Strategy
        st.subheader("5. Integration Strategy")
        with st.container(border=True):
            st.markdown(f"**Gateway:** {hld.integration_strategy.api_gateway_strategy}")
            st.markdown(f"**Contract:** {hld.integration_strategy.contract_strategy}")
            st.markdown("**Public APIs:**")
            render_bullets(hld.integration_strategy.public_apis)

        # 6. NFRs
        st.subheader("6. Non-Functional Requirements")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1: 
                st.markdown(f"**Scalability:** {hld.nfrs.scalability_plan}")
            with c2: 
                st.markdown(f"**Availability:** {hld.nfrs.availability_slo}")
            st.markdown(f"**Latency:** {hld.nfrs.latency_targets}")

        # 7. Security Compliance
        st.subheader("7. Security Compliance")
        with st.container(border=True):
            st.markdown(f"**AuthN/AuthZ:** {hld.security_compliance.authentication_strategy} / {hld.security_compliance.authorization_strategy}")
            st.markdown(f"**Encryption:** {hld.security_compliance.data_encryption_at_rest}")
            st.markdown("**Certifications:**")
            render_bullets(hld.security_compliance.compliance_certifications)

        # 8. Reliability & Resilience
        st.subheader("8. Reliability & Resilience")
        with st.container(border=True):
            st.markdown(f"**Failover:** {hld.reliability_resilience.failover_strategy}")
            st.markdown(f"**Circuit Breaker:** {hld.reliability_resilience.circuit_breaker_policy}")
            st.markdown(f"**DR (RPO/RTO):** {hld.reliability_resilience.disaster_recovery_rpo_rto}")

        # 9. Observability
        st.subheader("9. Observability Strategy")
        with st.container(border=True):
            st.markdown(f"**Logging:** {hld.observability.logging_strategy}")
            st.markdown(f"**Tracing:** {hld.observability.tracing_strategy}")
            st.markdown("**Metrics:**")
            render_bullets(hld.observability.metrics_collection)

        # 10. Deployment & Ops
        st.subheader("10. Deployment & Operations")
        with st.container(border=True):
            st.markdown(f"**Cloud:** {hld.deployment_ops.cloud_provider} ({hld.deployment_ops.deployment_model})")
            st.markdown(f"**CI/CD:** {hld.deployment_ops.cicd_pipeline}")
            st.markdown(f"**Rollback:** {hld.deployment_ops.rollback_strategy}")

        # 11. Design Decisions
        st.subheader("11. Design Decisions")
        with st.container(border=True):
            st.info(f"**Justification:** {hld.design_decisions.tech_stack_justification}")
            st.markdown(f"**Trade-offs:** {hld.design_decisions.trade_off_analysis}")
            st.markdown("**Rejected Alternatives:**")
            render_bullets(hld.design_decisions.rejected_alternatives)

    # ==========================================================================
    # TAB 2: LOW LEVEL DESIGN (LLD) - ALL 11 SECTIONS
    # ==========================================================================
    with tabs[1]:
        st.header("Low Level Design Document")
        if not verdict.is_valid:
            st.error(f"⚠️ **Judge Critique:** {verdict.critique}")

        # 1. Detailed Components
        st.subheader("1. Component Deep Dive")
        for comp in lld.detailed_components:
            with st.expander(f"⚙️ {comp.component_name}"):
                st.markdown(f"**Class Structure:** {comp.class_structure_desc}")
                st.markdown("**Interfaces:**")
                render_bullets(comp.interface_specifications)
                st.caption(f"Security: {comp.security_considerations}")

        # 2. API Design
        st.subheader("2. API Specifications")
        for api in lld.api_design:
            with st.container(border=True):
                st.markdown(f"**{api.method}** `{api.endpoint}`")
                c1, c2 = st.columns(2)
                with c1: st.code(api.request_schema, language="json")
                with c2: st.code(api.response_schema, language="json")
                st.caption(f"Auth: {api.authorization_mechanism}")

        # 3. Data Model Deep Dive
        st.subheader("3. Data Model")
        for dm in lld.data_model_deep_dive:
            with st.container(border=True):
                st.markdown(f"**Entity: {dm.entity}**")
                st.markdown(f"Attributes: {', '.join(dm.attributes)}")
                st.markdown(f"Indexes: {', '.join(dm.indexes)}")

        # 4. Business Logic
        st.subheader("4. Business Logic")
        with st.container(border=True):
            st.markdown(f"**Algorithms:** {lld.business_logic.core_algorithms}")
            st.markdown(f"**Concurrency:** {lld.business_logic.concurrency_control}")
            if lld.business_logic.state_machine_desc:
                st.markdown(f"**State Machine:** {lld.business_logic.state_machine_desc}")

        # 5. Consistency & Concurrency
        st.subheader("5. Consistency & Concurrency")
        with st.container(border=True):
            st.write(lld.consistency_concurrency)

        # 6. Error Handling
        st.subheader("6. Error Handling Strategy")
        with st.container(border=True):
            st.markdown(f"**Taxonomy:** {lld.error_handling.error_taxonomy}")
            st.markdown(f"**Retries:** {lld.error_handling.retry_policies}")
            st.markdown("**Codes:**")
            render_bullets(lld.error_handling.custom_error_codes)

        # 7. Security Implementation
        st.subheader("7. Security Implementation")
        with st.container(border=True):
            st.markdown(f"**Input Validation:** {lld.security_implementation.input_validation_rules}")
            st.markdown(f"**Token Mgmt:** {lld.security_implementation.token_management}")
            st.markdown(f"**Encryption:** {lld.security_implementation.encryption_details}")

        # 8. Performance Engineering
        st.subheader("8. Performance Engineering")
        with st.container(border=True):
            st.markdown(f"**Caching:** {lld.performance_engineering.caching_strategy}")
            st.markdown(f"**Invalidation:** {lld.performance_engineering.cache_invalidation}")
            st.markdown(f"**Async:** {lld.performance_engineering.async_processing_desc}")

        # 9. Testing Strategy
        st.subheader("9. Testing Strategy")
        with st.container(border=True):
            st.markdown(f"**Unit:** {lld.testing_strategy.unit_test_scope}")
            st.markdown(f"**Integration:** {lld.testing_strategy.integration_test_scope}")
            st.markdown(f"**Coverage Goal:** {lld.testing_strategy.test_coverage_metrics}")

        # 10. Operational Readiness
        st.subheader("10. Operational Readiness")
        with st.container(border=True):
            st.markdown(f"**Runbooks:** {lld.operational_readiness.runbook_summary}")
            st.markdown(f"**Backup/Restore:** {lld.operational_readiness.backup_recovery_procedures}")
            st.markdown("**Alerts:**")
            render_bullets(lld.operational_readiness.monitoring_and_alerts)

        # 11. Documentation Governance
        st.subheader("11. Documentation Governance")
        with st.container(border=True):
            st.markdown(f"**Standards:** {lld.documentation_governance.code_docs_standard}")
            st.markdown(f"**ADR Process:** {lld.documentation_governance.adr_process}")

    # ==========================================================================
    # TAB 3: ARTIFACTS
    # ==========================================================================
    with tabs[2]:
        st.header("Artifacts")

        # 1. Diagrams
        st.subheader("Architecture Diagrams")
        diag_path = res.get('diagram_path')
        if diag_path and os.path.exists(diag_path):
            st.image(diag_path, caption="Generated Architecture[Image of Architecture Diagram]", use_container_width=True)
            with open(diag_path, "rb") as file:
                st.download_button("📥 Download PNG", file, "architecture.png", "image/png")
        else:
            st.warning("No diagram generated.")

        with st.expander("View Diagram Code (Python)"):
            code_obj = res.get('diagram_code')
            # Handle different formats (Pydantic model, dict, or string)
            if code_obj:
                if hasattr(code_obj, 'python_code'):
                    st.code(code_obj.python_code, language='python')
                elif isinstance(code_obj, dict) and 'python_code' in code_obj:
                    st.code(code_obj['python_code'], language='python')
                elif hasattr(code_obj, 'system_context'): # Handle ArchitectureDiagrams object
                    st.code(f"# System Context\n{code_obj.system_context}\n\n# Container\n{code_obj.container_diagram}\n\n# Data Flow\n{code_obj.data_flow}", language='python')
                else:
                    st.code(str(code_obj), language='python')

        st.divider()

        # 2. Scaffolding
        st.subheader("Project Scaffolding")
        if scaffold:
            zip_bytes = create_zip_bytes(scaffold)
            st.download_button("📦 Download Code (.zip)", zip_bytes, "project_starter.zip", "application/zip", type="primary")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Folder Structure**")
                st.code(scaffold.folder_structure)
            with c2:
                st.markdown("**Files**")
                for f in scaffold.starter_files:
                    with st.expander(f.filename):
                        st.code(f.content)
        else:
            st.info("No scaffolding available.")

        st.divider()
        with st.expander("🕵️ Execution Logs"):
            for log in res.get('logs', []):
                st.text(f"[{log.get('time', '')}] {log.get('role', 'System')}: {log.get('message', '')}")