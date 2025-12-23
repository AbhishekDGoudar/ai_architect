import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from graph import app_graph
from schemas import HighLevelDesign, LowLevelDesign, JudgeVerdict
from storage import save_snapshot, list_snapshots, load_snapshot

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

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Settings")
    provider = st.selectbox("LLM", ["openai", "gemini", "claude", "ollama"], index=1)
    api_key = st.text_input("API Key", type="password", value=st.session_state.get("api_key", ""))
    st.session_state["api_key"] = api_key
    st.divider()
    selected_file = st.selectbox("Snapshots", ["(New)"] + list_snapshots())
    if selected_file != "(New)" and st.button("Load"):
        d = load_snapshot(selected_file)
        st.session_state["current_result"] = {
            "hld": HighLevelDesign(**d['hld']) if d.get('hld') else None,
            "lld": LowLevelDesign(**d['lld']) if d.get('lld') else None,
            "verdict": JudgeVerdict(**d['verdict']) if d.get('verdict') else None,
            "diagram_path": d.get("diagram_path"), "total_tokens": d.get("total_tokens", 0)
        }
        st.rerun()

st.title("🤖 AI Architect Studio")

if st.session_state.get("current_result") is None:
    p_name = st.text_input("Project Name")
    user_prompt = st.text_area("Requirements", height=150)
    if st.button("Generate", type="primary"):
        with st.status("🏗️ Architecting...") as status:
            state = {"user_request": user_prompt, "provider": provider, "api_key": api_key, "retry_count": 0, "total_tokens": 0}
            for event in app_graph.stream(state):
                for node, update in event.items():
                    state.update(update)
                    status.write(f"✅ {node.title()} complete.")
            st.session_state["current_result"] = state
            st.session_state["project_name"] = p_name
            st.rerun()
else:
    res = st.session_state["current_result"]
    hld: HighLevelDesign = res['hld']
    lld: LowLevelDesign = res['lld']
    
    tab_hld, tab_lld, tab_art = st.tabs(["🏛️ HLD Full", "💻 LLD Full", "📂 Artifacts"])

    with tab_hld:
        st.header(f"HLD: {st.session_state.get('project_name')} (v{hld.business_context.version})")
        
        # 1. Business Context
        with st.expander("1. Business Context", expanded=True):
            st.write(f"**Problem:** {hld.business_context.problem_statement}")
            c1, c2, c3 = st.columns(3)
            with c1: render_list(hld.business_context.business_goals, "Goals")
            with c2: render_list(hld.business_context.stakeholders, "Stakeholders")
            with c3: render_list(hld.business_context.change_log, "Change Log")
            render_list(hld.business_context.in_scope, "In Scope")
            render_list(hld.business_context.out_of_scope, "Out of Scope")
            render_list(hld.business_context.assumptions_constraints, "Constraints")

        # 2. Overview & 3. Components
        with st.expander("2 & 3. Architecture & Components"):
            st.info(f"**Style:** {hld.architecture_overview.style}")
            st.write(f"**Data Flow:** {hld.architecture_overview.data_flow_desc}")
            st.table(pd.DataFrame([{"Layer": i.layer, "Tech": i.technology} for i in hld.architecture_overview.tech_stack]))
            for c in hld.core_components:
                st.markdown(f"--- \n**Component: {c.name}**")
                st.write(f"*Responsibility:* {c.responsibility}")
                st.write(f"*Protocols:* {', '.join(c.communication_protocols)} | *Ownership:* {c.component_ownership}")

        # 4. Data
        with st.expander("4. Data Architecture"):
            st.write(f"**Consistency:** {hld.data_architecture.consistency_model} | **Classification:** {hld.data_architecture.data_classification}")
            st.write(f"**Backup:** {hld.data_architecture.data_backup_recovery}")
            st.write(f"**Retention:** {hld.data_architecture.data_retention_policy}")
            st.write(f"**Evolution:** {hld.data_architecture.schema_evolution_strategy}")

        # 5. Integration
        with st.expander("5. Integration Strategy"):
            st.write(f"**Gateway:** {hld.integration_strategy.api_gateway_strategy}")
            st.write(f"**Contract:** {hld.integration_strategy.contract_strategy} (v: {hld.integration_strategy.versioning_strategy})")
            render_list(hld.integration_strategy.public_apis, "Public Endpoints")

        # 6. NFRs
        with st.expander("6. Non-Functional Requirements"):
            st.write(f"**Scalability:** {hld.nfrs.scalability_plan}")
            st.write(f"**SLO:** {hld.nfrs.availability_slo} | **Latency:** {hld.nfrs.latency_targets}")
            st.write(f"**Cost:** {hld.nfrs.cost_constraints}")

        # 7-11. Security, Resilience, Ops, Decisions
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

    with tab_lld:
        st.header("Detailed Implementation Design")
        # 1. Components
        with st.expander("1. Internal Component Logic"):
            for dc in lld.detailed_components:
                st.markdown(f"**{dc.component_name}**")
                st.write(dc.class_structure_desc)
                st.caption(f"Security: {dc.security_considerations}")
        # 2. APIs
        with st.expander("2. API Specifications"):
            for api in lld.api_design:
                st.code(f"{api.method} {api.endpoint}\nAuth: {api.authorization_mechanism}", language="bash")
                st.write(f"**Response Schema:** {api.response_schema}")
        # 3. Data
        with st.expander("3. Database Deep Dive"):
            for dm in lld.data_model_deep_dive:
                st.markdown(f"**Entity: {dm.entity}**")
                st.write(f"Attributes: {', '.join(dm.attributes)}")
                st.write(f"Migration: {dm.migration_strategy}")
        # 4-11. Logic, Performance, Ops
        with st.expander("4. Business Logic & Algorithms"): st.write(lld.business_logic.core_algorithms)
        with st.expander("5. Concurrency Control"): st.write(lld.consistency_concurrency)
        with st.expander("6. Error Handling"): st.write(lld.error_handling.exception_handling_framework)
        with st.expander("7. Security Implementation"): st.write(lld.security_implementation.token_management)
        with st.expander("8. Performance Engineering"): st.write(lld.performance_engineering.caching_strategy)
        with st.expander("9. Testing Strategy"): st.write(lld.testing_strategy.unit_test_scope)
        with st.expander("10. Operational Readiness"): st.write(lld.operational_readiness.runbook_summary)
        with st.expander("11. Governance"): st.write(lld.documentation_governance.adr_process)

    with tab_art:
        if res.get('diagram_path'): st.image(res['diagram_path'])
        if st.button("New Session"): st.session_state["current_result"] = None; st.rerun()