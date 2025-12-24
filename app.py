import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import shutil
import os
import time
import agents 
from graph import app_graph
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict, ProjectStructure
from storage import save_snapshot, list_snapshots, load_snapshot
from tools import generate_scaffold
from model_factory import get_llm
from callbacks import TokenMeter

st.set_page_config(page_title="AI Architect Studio", page_icon="🏗️", layout="wide")

# --- UI Helpers ---
def render_list(items, label):
    st.markdown(f"**{label}:**")
    if not items: st.caption("None")
    else: st.markdown("\n".join([f"- {i}" for i in items]))

def render_box(title, content):
    with st.container(border=True):
        st.subheader(title)
        st.write(content)

def get_progress_visual(current_step: str):
    """
    Returns a markdown string representing the pipeline progress.
    """
    steps = [
        ("manager", "Manager"),
        ("security", "Security"),
        ("team_lead", "Team Lead"),
        ("judge", "Judge"),
        ("refiner", "Refinement"),
        ("visuals", "Visuals"),
        ("validator", "Validator")
    ]
    
    visual_parts = []
    for step_id, label in steps:
        if step_id == current_step:
            visual_parts.append(f"**▶️ {label}**")
        else:
            visual_parts.append(f"{label}")
            
    return " → ".join(visual_parts)

def get_progress_value(node_name: str) -> int:
    """Maps graph nodes to a 0-100 progress value."""
    mapping = {
        "manager": 10,
        "security": 30,
        "team_lead": 50,
        "judge": 70,
        "refiner": 60,
        "visuals": 90,
        "validator": 95,
        "done": 100
    }
    return mapping.get(node_name, 0)

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Settings")
    provider = st.selectbox("LLM", ["openai", "gemini", "claude", "ollama"], index=1)
    api_key = st.text_input("API Key", type="password", value=st.session_state.get("api_key", ""))
    st.session_state["api_key"] = api_key
    st.divider()
    
    selected_file = st.selectbox("Snapshots", ["(New)"] + list_snapshots())
    
    if selected_file != "(New)" and st.button("Load"):
        # UPDATED LOADING LOGIC (Fixes the crash)
        try:
            d = load_snapshot(selected_file)
            
            # 'd' now contains real Pydantic objects from storage.py. 
            # We don't need to reconstruct them manually.
            
            # Inject current session settings
            d["api_key"] = api_key
            if "provider" not in d:
                d["provider"] = d.get("metrics", {}).get("provider", provider)
            
            st.session_state["current_result"] = d
            st.success(f"Loaded {selected_file}")
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"Error loading snapshot: {e}")

# --- Main App ---
st.title("🤖 AI Architect Studio")

if st.session_state.get("current_result") is None:
    p_name = st.text_input("Project Name", value="MyGenAIApp")
    user_prompt = st.text_area("Requirements", height=150)
    
    if st.button("Generate Architecture", type="primary"):
        if not api_key and provider != "ollama":
             st.error("Please enter an API Key.")
             st.stop()
             
        progress_bar = st.progress(0)
        step_display = st.empty()
        
        with st.status("🏗️ Architecting Solution...", expanded=True) as status:
            state = {"user_request": user_prompt, "provider": provider, "api_key": api_key, "retry_count": 0, "total_tokens": 0}
            
            step_display.markdown(get_progress_visual("start"))
            
            for event in app_graph.stream(state):
                for node, update in event.items():
                    state.update(update)
                    
                    prog_val = get_progress_value(node)
                    progress_bar.progress(prog_val)
                    step_display.markdown(get_progress_visual(node))
                    
                    if "logs" in update:
                        log_entry = update['logs'][0]
                        status.write(f"**{log_entry['role']}**: {log_entry['message']}")
            
            progress_bar.progress(100)
            step_display.markdown("✅ **Architecture Generation Complete**")
            
            st.session_state["current_result"] = state
            st.session_state["project_name"] = p_name
            st.rerun()

else:
    res = st.session_state["current_result"]
    hld: HighLevelDesign = res.get('hld')
    lld: LowLevelDesign = res.get('lld')
    scaffold: ProjectStructure = res.get('scaffold')
    
    # --- Toolbar ---
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if st.button("💾 Save Snapshot"):
            fname = save_snapshot(st.session_state.get("project_name", "Untitled"), res)
            if fname: st.success(f"Saved: {fname}")
    with c2:
        if st.button("🔄 New Session"):
            st.session_state["current_result"] = None
            st.rerun()

    # --- Tabs ---
    tab_hld, tab_lld, tab_code, tab_art = st.tabs(["🏛️ HLD Full", "💻 LLD Full", "🛠️ Code", "📂 Diagrams"])

    # 1. HLD TAB
    with tab_hld:
        if hld:
            st.header(f"HLD: {st.session_state.get('project_name')} (v{hld.business_context.version})")
            
            with st.expander("1. Business Context", expanded=True):
                st.write(f"**Problem:** {hld.business_context.problem_statement}")
                c1, c2, c3 = st.columns(3)
                with c1: render_list(hld.business_context.business_goals, "Goals")
                with c2: render_list(hld.business_context.stakeholders, "Stakeholders")
                with c3: render_list(hld.business_context.change_log, "Change Log")
                render_list(hld.business_context.in_scope, "In Scope")
                render_list(hld.business_context.out_of_scope, "Out of Scope")
                render_list(hld.business_context.assumptions_constraints, "Constraints")

            with st.expander("2 & 3. Architecture & Components"):
                st.info(f"**Style:** {hld.architecture_overview.style}")
                st.write(f"**Data Flow:** {hld.architecture_overview.data_flow_desc}")
                st.table(pd.DataFrame([{"Layer": i.layer, "Tech": i.technology} for i in hld.architecture_overview.tech_stack]))
                for c in hld.core_components:
                    st.markdown(f"--- \n**Component: {c.name}**")
                    st.write(f"*Responsibility:* {c.responsibility}")
                    st.write(f"*Protocols:* {', '.join(c.communication_protocols)} | *Ownership:* {c.component_ownership}")

            with st.expander("4. Data Architecture"):
                st.write(f"**Consistency:** {hld.data_architecture.consistency_model} | **Classification:** {hld.data_architecture.data_classification}")
                st.write(f"**Backup:** {hld.data_architecture.data_backup_recovery}")
                st.write(f"**Retention:** {hld.data_architecture.data_retention_policy}")
                st.write(f"**Evolution:** {hld.data_architecture.schema_evolution_strategy}")

            with st.expander("5. Integration Strategy"):
                st.write(f"**Gateway:** {hld.integration_strategy.api_gateway_strategy}")
                st.write(f"**Contract:** {hld.integration_strategy.contract_strategy} (v: {hld.integration_strategy.versioning_strategy})")
                render_list(hld.integration_strategy.public_apis, "Public Endpoints")

            with st.expander("6. Non-Functional Requirements"):
                st.write(f"**Scalability:** {hld.nfrs.scalability_plan}")
                st.write(f"**SLO:** {hld.nfrs.availability_slo} | **Latency:** {hld.nfrs.latency_targets}")
                st.write(f"**Cost:** {hld.nfrs.cost_constraints}")

            with st.expander("7. Security & Compliance"):
                st.write(f"**Auth Strategy:** {hld.security_compliance.authentication_strategy}")
                st.write(f"**Encryption (Rest):** {hld.security_compliance.data_encryption_at_rest}")
                st.write(f"**Encryption (Transit):** {hld.security_compliance.data_encryption_in_transit}")
            with st.expander("8. Reliability & Resilience"):
                st.write(f"**Failover:** {hld.reliability_resilience.failover_strategy}")
                st.write(f"**Circuit Breaker:** {hld.reliability_resilience.circuit_breaker_policy}")
            with st.expander("9. Observability"):
                render_list(hld.observability.metrics_collection, "KPIs")
                st.write(f"**Tracing:** {hld.observability.tracing_strategy}")
            with st.expander("10. Deployment & Ops"):
                st.write(f"**Cloud:** {hld.deployment_ops.cloud_provider} | **Model:** {hld.deployment_ops.deployment_model}")
                st.write(f"**Strategy:** {hld.deployment_ops.deployment_strategy} | **CI/CD:** {hld.deployment_ops.cicd_pipeline}")
            with st.expander("11. Design Decisions"):
                st.warning(hld.design_decisions.tech_stack_justification)
                render_list(hld.design_decisions.trade_off_analysis, "Trade-offs")

    # 2. LLD TAB
    with tab_lld:
        if lld:
            st.header("Detailed Implementation Design")
            with st.expander("1. Internal Component Logic"):
                for dc in lld.detailed_components:
                    st.markdown(f"**{dc.component_name}**")
                    st.write(dc.class_structure_desc)
                    st.caption(f"Security: {dc.security_considerations}")
            with st.expander("2. API Specifications"):
                for api in lld.api_design:
                    st.code(f"{api.method} {api.endpoint}\nAuth: {api.authorization_mechanism}", language="bash")
                    st.write(f"**Response Schema:** {api.response_schema}")
            with st.expander("3. Database Deep Dive"):
                for dm in lld.data_model_deep_dive:
                    st.markdown(f"**Entity: {dm.entity}**")
                    st.write(f"Attributes: {', '.join(dm.attributes)}")
                    st.write(f"Migration: {dm.migration_strategy}")
            with st.expander("4. Business Logic & Algorithms"): st.write(lld.business_logic.core_algorithms)
            with st.expander("5. Concurrency Control"): st.write(lld.consistency_concurrency)
            with st.expander("6. Error Handling"): st.write(lld.error_handling.exception_handling_framework)
            with st.expander("7. Security Implementation"): st.write(lld.security_implementation.token_management)
            with st.expander("8. Performance Engineering"): st.write(lld.performance_engineering.caching_strategy)
            with st.expander("9. Testing Strategy"): st.write(lld.testing_strategy.unit_test_scope)
            with st.expander("10. Operational Readiness"): st.write(lld.operational_readiness.runbook_summary)
            with st.expander("11. Governance"): st.write(lld.documentation_governance.adr_process)

    # 3. CODE TAB (Manual Scaffolding Trigger)
    with tab_code:
        st.header("Project Scaffolding")
        
        if scaffold:
            st.success(f"✅ Generated {len(scaffold.starter_files)} starter files.")
            for f in scaffold.starter_files:
                with st.expander(f"📄 {f.filename}"):
                    st.code(f.content)
            
            if st.button("📦 Download ZIP"):
                output_dir = f"./output/{st.session_state.get('project_name','app')}"
                generate_scaffold(scaffold, output_dir=output_dir)
                shutil.make_archive(output_dir, 'zip', output_dir)
                with open(f"{output_dir}.zip", "rb") as f:
                    st.download_button("⬇️ Download ZIP", f, file_name=f"{st.session_state.get('project_name','app')}.zip")
        else:
            if lld:
                st.info("Low Level Design is ready. You can now generate the starter code.")
                if st.button("🚀 Generate Scaffolding Now", type="primary"):
                    with st.spinner("👷 DevOps Agent is working..."):
                        llm = get_llm(res['provider'], res['api_key'], "fast")
                        meter = TokenMeter()
                        try:
                            new_scaffold = agents.scaffold_architect(lld, llm, meter)
                            st.session_state["current_result"]["scaffold"] = new_scaffold
                            st.session_state["current_result"]["total_tokens"] += meter.total_tokens
                            st.rerun()
                        except Exception as e:
                            st.error(f"Scaffolding failed: {str(e)}")
            else:
                st.warning("You must generate the LLD (Phase 1) before you can scaffold code.")

    # 4. DIAGRAMS TAB
    with tab_art:
        st.header("Architecture Diagrams")
        if res.get('diagram_path') and os.path.exists(res['diagram_path']):
            st.image(res['diagram_path'], caption="System Architecture")
            st.caption(f"Source: {res['diagram_path']}")
        elif res.get('diagram_code'):
             st.warning("Diagram code generated, but rendering failed.")
             st.code(res['diagram_code'].system_context, language='python')
        else:
            st.info("No diagrams available.")