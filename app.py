import streamlit as st
import pandas as pd
import shutil
import os
import time
from datetime import datetime
import agents
from graph import app_graph
from schemas import HighLevelDesign, LowLevelDesign
from storage import save_snapshot, list_snapshots, load_snapshot, delete_snapshot
from tools import generate_scaffold
from model_factory import get_llm
from callbacks import TokenMeter
from rag import knowledge  # Knowledge base engine
import streamlit.components.v1 as components

st.set_page_config(page_title="AI Architect Studio", page_icon="🏗️", layout="wide")

class Component:
    def __init__(self, name, class_structure_desc, module_boundaries, method_details, interface_specifications, dependency_direction, versioning, error_handling_local, security_considerations):
        self.component_name = name
        self.class_structure_desc = class_structure_desc
        self.module_boundaries = module_boundaries
        self.method_details = method_details
        self.interface_specifications = interface_specifications
        self.dependency_direction = dependency_direction
        self.versioning = versioning
        self.error_handling_local = error_handling_local
        self.security_considerations = security_considerations

# ==========================================
# 🧠 SESSION STATE INITIALIZATION
# ==========================================
if "project_state" not in st.session_state:
    st.session_state["project_state"] = {
        "hld": None,
        "lld": None,
        "scaffold": None,
        "diagram_code": None,
        "diagram_path": None,
        "logs": [],
        "total_tokens": 0,
        "provider": "gemini", # Default
        "user_request": "",
        "project_name": "MyGenAIApp"
    }

if "running_task" not in st.session_state:
    st.session_state["running_task"] = None  # Tracks which task is currently running

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def render_card(title, body_html, bg_color="#FFFFFF", accent="#333"):
    """
    Renders a fixed-height card with a very light background by default and rounded corners.
    """
    st.markdown(
        f"""
        <div style="
            background-color:{bg_color};
            padding:16px;
            margin-bottom:16px;
            border-left:6px solid {accent};
            border:1px solid rgba(0,0,0,0.08);
            height:225px;        /* fixed height */
            overflow:auto;       /* scroll if content is too long */
            border-radius:12px;  /* rounded corners */
        ">
            <h5 style="margin-top:0;">{title}</h5>
            {body_html}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_cards_2_per_row(items, render_fn=render_card, item_per_row=2):
    """
    Renders cards in rows of `item_per_row`, defaulting to render_card.
    """
    for i in range(0, len(items), item_per_row):
        cols = st.columns(item_per_row)
        for j, item in enumerate(items[i:i+item_per_row]):
            with cols[j]:
                render_fn(item)


def calculate_cost(tokens, provider):
    # Rough estimates per 1M tokens (blended input/output)
    rates = {
        "openai": 0.50,   # GPT-4o-mini approx
        "gemini": 0.20,   # Flash approx
        "claude": 1.00,   # Haiku approx
        "ollama": 0.00
    }
    rate = rates.get(provider, 0.0)
    cost = (tokens / 1_000_000) * rate
    return f"${cost:.4f}"


def render_list(items, label):
    # Bold label
    st.markdown(f"**{label}:**")
    
    # If no items, show "None" in caption style
    if not items:
        st.caption("None")
    else:
        # Join items as a bullet list
        st.markdown("\n".join([f"- {item}" for item in items]))


def render_markdown_card(title, body):
    st.markdown(f"### {title}")  # Sub-header for title (h3)
    st.markdown(body)  # Body content

def render_mermaid(code: str, height=500):
    """
    Renders Mermaid.js diagram using a lightweight HTML component.
    """
    html_code = f"""
    <div class="mermaid" style="height: {height}px; overflow: auto;">
    {code}
    </div>
    <script type="module">
      import mermaid from '[https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs](https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs)';
      mermaid.initialize({{ startOnLoad: true }});
    </script>
    """
    components.html(html_code, height=height)


def display_hld(hld: HighLevelDesign, container):
    """Renders the FULL HLD content into a specific container."""
    if not hld: return
    with container:
        # Header
        st.header(f"HLD: {st.session_state.get('project_name', 'Project')} (v{hld.business_context.version})")
        
        # Business Context
        with st.expander("1. Business Context", expanded=True):
            st.write(f"**Problem:** {hld.business_context.problem_statement}")
            c1, c2, = st.columns(2)
            c3, c4, = st.columns(2)
            c5, c6, = st.columns(2)
            with c1: render_list(hld.business_context.business_goals, "Goals")
            with c2: render_list(hld.business_context.non_goals, "Non-goals")

            with c3: render_list(hld.business_context.in_scope, "IN Scope")
            with c4: render_list(hld.business_context.out_of_scope, "Out of Scope")
            
            with c5: render_list(hld.business_context.assumptions_constraints, "Constraints")
            with c6: render_list(hld.business_context.stakeholders, "Stakeholders")
            
            render_list(hld.business_context.change_log, "Change Log")
            
            

        # Architecture Overview
        with st.expander("2 & 3. Architecture Overview & Components", expanded=True):
            st.info(f"**Style:** {hld.architecture_overview.style}")
            st.write(f"**External Interfaces:** {', '.join(hld.architecture_overview.external_interfaces)}")
            st.write(f"**User Stories:** {', '.join(hld.architecture_overview.user_stories)}")
            
            # Tech Stack
            if hld.architecture_overview.tech_stack:
                st.markdown("<h6 style='font-size: 14px;'>Tech Rationale</h6>", unsafe_allow_html=True)
                st.table(pd.DataFrame([{"Layer": i.layer, "Tech": i.technology} for i in hld.architecture_overview.tech_stack]))
            
            if hld.architecture_overview.layer_tech_rationale:
                st.markdown("<h6 style='font-size: 14px;'>Tech Rationale</h6>", unsafe_allow_html=True)
                st.table(pd.DataFrame([{"Tech": i.technology, "Rationale": i.rationale, "Trade-offs": i.tradeoffs} for i in hld.architecture_overview.layer_tech_rationale]))



            # Event Flows
            render_cards_2_per_row(
                hld.architecture_overview.event_flows,
                lambda flow: render_card(
                    title="Event Flow",
                    body_html=(
                        f"<p>{flow.description}</p>"
                        f"<p><b>Components Involved:</b> {', '.join(flow.components_involved)}</p>"
                        f"<p><b>Event Types:</b> {', '.join(flow.event_types)}</p>"
                    ),
                    bg_color="#F4F2F2",  # ultra-light green
                    accent="#2E7D32"
                )
            )

            # KPIs
            render_cards_2_per_row(
                hld.architecture_overview.kpis,
                lambda kpi: render_card(
                    title=f"KPI Goal: {kpi.goal}",
                    body_html=(
                        f"<p><b>Metric:</b> {kpi.metric}</p>"
                        + (f"<p><b>Target Value:</b> {kpi.target_value}</p>" if kpi.target_value else "")
                    ),
                    bg_color="#F4F2F2",  # ultra-light orange
                    accent="#EF6C00"
                )
            )



        # Data Architecture
        with st.expander("4. Data Architecture", expanded=True):
            st.write(f"**Data Classification:** {hld.data_architecture.data_classification}")
            st.write(f"**Consistency Model:** {hld.data_architecture.consistency_model}")
            st.write(f"**Data Retention Policy:** {hld.data_architecture.data_retention_policy}")
            st.write(f"**Data Backup and Recovery:** {hld.data_architecture.data_backup_recovery}")
            st.write(f"**Schema Evolution Strategy:** {hld.data_architecture.schema_evolution_strategy}")

        # Integration Strategy
        with st.expander("5. Integration Strategy", expanded=True):
            render_list(hld.integration_strategy.public_apis, "Public APIs")
            render_list(hld.integration_strategy.internal_apis, "Internal APIs")
            st.write(f"**API Gateway Strategy:** {hld.integration_strategy.api_gateway_strategy}")
            st.write(f"**Contract Strategy:** {hld.integration_strategy.contract_strategy}")
            st.write(f"**Versioning Strategy:** {hld.integration_strategy.versioning_strategy}")
            st.write(f"**Backward Compatibility Plan:** {hld.integration_strategy.backward_compatibility_plan}")

        # NFRs (Non-Functional Requirements)
        with st.expander("6. Non-Functional Requirements", expanded=True):
            st.write(f"**Scalability Plan:** {hld.nfrs.scalability_plan}")
            st.write(f"**Availability SLO:** {hld.nfrs.availability_slo}")
            st.write(f"**Latency Targets:** {hld.nfrs.latency_targets}")
            render_list(hld.nfrs.security_requirements, "Security Requirements")
            st.write(f"**Reliability Targets:** {hld.nfrs.reliability_targets}")
            st.write(f"**Maintainability Plan:** {hld.nfrs.maintainability_plan}")
            st.write(f"**Cost Constraints:** {hld.nfrs.cost_constraints}")
            st.write(f"**Load Testing Strategy:** {hld.nfrs.load_testing_strategy}")

        # Security & Compliance
        with st.expander("7. Security & Compliance", expanded=True):
            st.write(f"**Threat Model Summary:** {hld.security_compliance.threat_model_summary}")
            st.write(f"**Authentication Strategy:** {hld.security_compliance.authentication_strategy}")
            st.write(f"**Authorization Strategy:** {hld.security_compliance.authorization_strategy}")
            st.write(f"**Secrets Management:** {hld.security_compliance.secrets_management}")
            st.write(f"**Data Encryption (Rest):** {hld.security_compliance.data_encryption_at_rest}")
            st.write(f"**Data Encryption (Transit):** {hld.security_compliance.data_encryption_in_transit}")
            st.write(f"**Auditing Mechanisms:** {hld.security_compliance.auditing_mechanisms}")
            render_list(hld.security_compliance.compliance_certifications, "Compliance Certifications")

        # Reliability & Resilience
        with st.expander("8. Reliability & Resilience", expanded=True):
            st.write(f"**Failover Strategy:** {hld.reliability_resilience.failover_strategy}")
            st.write(f"**Disaster Recovery (RPO/RTO):** {hld.reliability_resilience.disaster_recovery_rpo_rto}")
            st.write(f"**Self-Healing Mechanisms:** {hld.reliability_resilience.self_healing_mechanisms}")
            st.write(f"**Retry/Backoff Strategy:** {hld.reliability_resilience.retry_backoff_strategy}")
            st.write(f"**Circuit Breaker Policy:** {hld.reliability_resilience.circuit_breaker_policy}")

        # Observability
        with st.expander("9. Observability", expanded=True):
            render_list(hld.observability.metrics_collection, "Metrics Collection")
            st.write(f"**Tracing Strategy:** {hld.observability.tracing_strategy}")
            render_list(hld.observability.alerting_rules, "Alerting Rules")

        # Deployment & Operations
        with st.expander("10. Deployment & Operations", expanded=True):
            st.write(f"**Cloud Provider:** {hld.deployment_ops.cloud_provider}")
            st.write(f"**Deployment Model:** {hld.deployment_ops.deployment_model}")
            st.write(f"**CI/CD Pipeline:** {hld.deployment_ops.cicd_pipeline}")
            st.write(f"**Deployment Strategy:** {hld.deployment_ops.deployment_strategy}")
            st.write(f"**Feature Flag Strategy:** {hld.deployment_ops.feature_flag_strategy}")
            st.write(f"**Rollback Strategy:** {hld.deployment_ops.rollback_strategy}")
            st.write(f"**Operational Monitoring:** {hld.deployment_ops.operational_monitoring}")
            st.write(f"**Git Repository Management:** {hld.deployment_ops.git_repository_management}")

        # Design Decisions
        with st.expander("11. Design Decisions", expanded=True):
            render_list(hld.design_decisions.patterns_used, "Patterns Used")
            st.write(f"**Tech Stack Justification:** {hld.design_decisions.tech_stack_justification}")
            st.write(f"**Trade-off Analysis:** {hld.design_decisions.trade_off_analysis}")
            render_list(hld.design_decisions.rejected_alternatives, "Rejected Alternatives")

        # Citations
        with st.expander("12. Citations", expanded=True):
            for i, citation in enumerate(hld.citations, 1):
                st.markdown(f"{i}.  **Source:** {citation.source}  \n**Description:** {citation.description}")



def display_lld(lld: LowLevelDesign, container):
    """Renders the FULL LLD content into a specific container."""
    if not lld:
        return
    with container:
        st.header("Low-Level Design (LLD)")

        # Accordion component
        with st.expander("1. Internal Component Logic", expanded=True):
            for i, dc in enumerate(lld.detailed_components):
                # Replace divider with an accordion for each component
                with st.expander(f"Component {i+1}: {dc.component_name}"):
                    # --- 1. HEADER: Component Name & Class Structure ---
                    st.subheader(dc.component_name)
                    st.markdown("**Class Structure Definition**")
                    # st.info creates a colored highlight box without needing an icon
                    st.info(dc.class_structure_desc)

                    st.caption(f"**Module Boundaries:** {dc.module_boundaries}")

                    # --- 2. DETAILS: Tabbing Strategy ---
                    # Clean text labels for tabs
                    tab_methods, tab_interfaces, tab_specs = st.tabs([
                        "Methods", 
                        "Interfaces", 
                        "Specifications"
                    ])

                    # --- TAB A: Methods ---
                    with tab_methods:
                        if dc.method_details:
                            for method in dc.method_details:
                                # A bordered container creates a clean "Card" look
                                with st.container():
                                     with st.expander(f"#### {method.method_name}", expanded=False):
                                        # Top row: Method Name and Purpose
                                        # st.markdown(f"#### {method.method_name}") 
                                        st.markdown(f"**Purpose:** {method.purpose}")
                                        st.markdown(f"**Algorithm:** {method.algorithm_summary}")
                                        
                                        # Bottom: Technical I/O (Hidden by default to reduce noise)
                                   
                                        c1, c2 = st.columns(2)
                                        with c1:
                                            st.markdown("**Input Parameters**")
                                            st.code(', '.join(method.input_params), language="text")
                                        with c2:
                                            st.markdown("**Output**")
                                            st.code(method.output, language="text")
                        else:
                            st.caption("No specific methods defined for this component.")

                    # --- TAB B: Interfaces ---
                    with tab_interfaces:
                        if dc.interface_specifications:
                            st.markdown("**Interface List**")
                            for interface in dc.interface_specifications:
                                st.markdown(f"* {interface}")
                        else:
                            st.caption("No interface specifications listed.")

                    # --- TAB C: Specifications (Grid Layout) ---
                    with tab_specs:
                        c1, c2 = st.columns(2)
                        
                        with c1:
                            st.markdown("##### Dependency & Versioning")
                            st.markdown(f"**Dependency Direction:** {dc.dependency_direction}")
                            st.markdown(f"**Versioning:** {dc.versioning}")
                        
                        with c2:
                            st.markdown("##### Reliability & Security")
                            st.markdown(f"**Error Handling:** {dc.error_handling_local}")
                            st.markdown(f"**Security Considerations:** {dc.security_considerations}")

        # 2. API Design
        with st.expander("2. API Design", expanded=True):
            for i, api in enumerate(lld.api_design):
                if i > 0:
                    st.divider()
                
                # Create a specific container for each API Endpoint to frame it distinctly
                with st.container(border=True):
                    
                    # --- 1. HEADER: Endpoint & Method ---
                    # Using columns to put the Method (GET/POST) next to the Endpoint path
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        # Display HTTP Method with bold emphasis or color if supported
                        # (Using standard markdown headers for hierarchy)
                        st.markdown(f"### `{api.method}`") 
                    with c2:
                        st.markdown(f"### {api.endpoint}")

                    # --- 2. TABS: Contract vs. Operations ---
                    tab_contract, tab_ops, tab_qa = st.tabs([
                        "Data Contract", 
                        "Configuration & Security", 
                        "Quality Assurance"
                    ])

                    # --- TAB A: Data Contract (Schemas) ---
                    with tab_contract:
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            st.markdown("**Request Schema**")
                            # st.code provides a nice 'technical' look for schemas (JSON/Structs)
                            st.code(str(api.request_schema), language="json")
                        with sc2:
                            st.markdown("**Response Schema**")
                            st.code(str(api.response_schema), language="json")

                    # --- TAB B: Configuration (Auth, Limits) ---
                    with tab_ops:
                        c_op1, c_op2, c_op3 = st.columns(3)
                        with c_op1:
                            st.markdown("**Authorization**")
                            st.info(api.authorization_mechanism)
                        with c_op2:
                            st.markdown("**Rate Limiting**")
                            st.markdown(f"`{api.rate_limiting_rule}`")
                        with c_op3:
                            st.markdown("**Gateway Integration**")
                            st.markdown(api.api_gateway_integration)

                    # --- TAB C: QA (Errors, Testing, Versioning) ---
                    with tab_qa:
                        # Error Codes - check if it's a list or dict to format nicely
                        st.markdown("**Error Codes**")
                        if isinstance(api.error_codes, list):
                            # Render as bullet points if list
                            for err in api.error_codes:
                                st.markdown(f"- `{err}`")
                        else:
                            st.markdown(str(api.error_codes))

                        st.markdown("---")
                        
                        # Testing & Versioning side by side
                        qa1, qa2 = st.columns(2)
                        with qa1:
                            st.markdown("**Testing Strategy**")
                            st.caption(api.testing_strategy)
                        with qa2:
                            st.markdown("**Versioning Strategy**")
                            st.caption(api.versioning_strategy)

        # 3. Data Model Deep Dive
        with st.expander("3. Data Model Deep Dive", expanded=True):
            for i, data_model in enumerate(lld.data_model_deep_dive):
                if i > 0:
                    st.divider()

                # --- 1. HEADER: Entity Name ---
                # Using a recognizable icon/header for the table/entity
                st.subheader(f"{data_model.entity}")
                
                # --- 2. TABS: Schema vs. Usage vs. Management ---
                tab_schema, tab_usage, tab_ops = st.tabs([
                    "Schema Definition",
                    "Access Patterns", 
                    "Migration & Ops"
                ])

                # --- TAB A: Schema Definition (Structure) ---
                with tab_schema:
                    # Layout: Attributes on Left (Main), Constraints/Keys on Right (Metadata)
                    c_left, c_right = st.columns([2, 1])
                    
                    with c_left:
                        st.markdown("**Attributes**")
                        # Check if attributes exist and list them cleanly
                        if data_model.attributes:
                            for attr in data_model.attributes:
                                st.markdown(f"- `{attr}`")
                        else:
                            st.caption("No specific attributes defined.")
                            
                    with c_right:
                        st.markdown("**Constraints & Keys**")
                        with st.container(border=True):
                            if data_model.constraints:
                                st.caption("**Constraints:**")
                                for c in data_model.constraints:
                                    st.markdown(f"• {c}")
                            
                            if data_model.foreign_keys:
                                st.caption("**Foreign Keys:**")
                                for fk in data_model.foreign_keys:
                                    st.markdown(f"• {fk}")

                            if data_model.indexes:
                                st.caption("**Indexes:**")
                                for idx in data_model.indexes:
                                    st.markdown(f"• `{idx}`")

                        # Validation Rules moved here to sit with constraints
                        if data_model.validation_rules:
                            with st.expander("View Validation Rules"):
                                for rule in data_model.validation_rules:
                                    st.markdown(f"- {rule}")

                # --- TAB B: Access Patterns (Usage) ---
                with tab_usage:
                    if data_model.access_patterns:
                        for idx, ap in enumerate(data_model.access_patterns):
                            with st.container(border=True):
                                st.markdown(f"**Pattern {idx+1}:** {ap.pattern_description}")
                                
                                # Access Pattern Details
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.caption(f"**Target Entity:** {ap.entity}")
                                with c2:
                                    st.caption(f"**Lifecycle:** {ap.lifecycle_notes}")
                                
                                # Example Queries in Code Block for Syntax Highlighting
                                if ap.example_queries:
                                    st.markdown("**Example Queries:**")
                                    queries_text = "\n".join(ap.example_queries)
                                    st.code(queries_text, language="sql")
                    else:
                        st.info("No specific access patterns documented.")

                # --- TAB C: Migration & Operations ---
                with tab_ops:
                    st.markdown("##### Migration Strategy")
                    st.info(data_model.migration_strategy)

        # 4. Business Logic
        with st.expander("4. Business Logic", expanded=True):
            st.write(f"**Core Algorithms:** {lld.business_logic.core_algorithms}")
            st.write(f"**State Machine Description:** {lld.business_logic.state_machine_desc}")
            st.write(f"**Concurrency Control:** {lld.business_logic.concurrency_control}")
            st.write(f"**Async Processing Details:** {lld.business_logic.async_processing_details}")

        # 5. Error Handling Strategy
        with st.expander("5. Error Handling Strategy", expanded=True):
            st.write(f"**Error Taxonomy:** {lld.error_handling.error_taxonomy}")
            render_list(lld.error_handling.custom_error_codes, "Custom Error Codes")
            st.write(f"**Retry Policies:** {lld.error_handling.retry_policies}")
            st.write(f"**DLQ Strategy:** {lld.error_handling.dlq_strategy}")
            st.write(f"**Exception Handling Framework:** {lld.error_handling.exception_handling_framework}")

        # 6. Security Implementation
        with st.expander("6. Security Implementation", expanded=True):
            st.write(f"**Input Validation Rules:** {lld.security_implementation.input_validation_rules}")
            st.write(f"**Auth Flow Diagram Description:** {lld.security_implementation.auth_flow_diagram_desc}")
            st.write(f"**Token Management:** {lld.security_implementation.token_management}")
            st.write(f"**Encryption Details:** {lld.security_implementation.encryption_details}")

        # 7. Performance Engineering
        with st.expander("7. Performance Engineering", expanded=True):
            st.write(f"**Caching Strategy:** {lld.performance_engineering.caching_strategy}")
            st.write(f"**Cache Invalidation:** {lld.performance_engineering.cache_invalidation}")
            st.write(f"**Async Processing Description:** {lld.performance_engineering.async_processing_desc}")
            st.write(f"**Load Balancing Strategy:** {lld.performance_engineering.load_balancing_strategy}")

        # 8. Testing Strategy
        with st.expander("8. Testing Strategy", expanded=True):
            st.write(f"**Unit Test Scope:** {lld.testing_strategy.unit_test_scope}")
            st.write(f"**Integration Test Scope:** {lld.testing_strategy.integration_test_scope}")
            st.write(f"**Contract Testing Tools:** {lld.testing_strategy.contract_testing_tools}")
            st.write(f"**Chaos Engineering Plan:** {lld.testing_strategy.chaos_engineering_plan}")
            st.write(f"**Test Coverage Metrics:** {lld.testing_strategy.test_coverage_metrics}")

        # 9. Operational Readiness
        with st.expander("9. Operational Readiness", expanded=True):
            st.write(f"**Runbook Summary:** {lld.operational_readiness.runbook_summary}")
            st.write(f"**Incident Response Plan:** {lld.operational_readiness.incident_response_plan}")
            render_list(lld.operational_readiness.monitoring_and_alerts, "Monitoring & Alerts")
            st.write(f"**Backup & Recovery Procedures:** {lld.operational_readiness.backup_recovery_procedures}")

        # 10. Documentation Governance
        with st.expander("10. Documentation Governance", expanded=True):
            st.write(f"**Code Docs Standard:** {lld.documentation_governance.code_docs_standard}")
            st.write(f"**API Docs Tooling:** {lld.documentation_governance.api_docs_tooling}")
            st.write(f"**ADR Process:** {lld.documentation_governance.adr_process}")
            st.write(f"**Document Review Process:** {lld.documentation_governance.document_review_process}")
            st.write(f"**Internal vs Public Docs:** {lld.documentation_governance.internal_vs_public_docs}")

        # 11. Test Traceability
        with st.expander("11. Test Traceability", expanded=True):
            for test_trace in lld.test_traceability:
                st.write(f"**Requirement:** {test_trace.requirement}")
                render_list(test_trace.test_case_ids, "Test Case IDs")
                st.write(f"**Coverage Status:** {test_trace.coverage_status}")

        # Citations
        with st.expander("12. Citations", expanded=True):
            for citation in lld.citations:
                st.markdown(f"{i}.  **Source:** {citation.source}  \n**Description:** {citation.description}")

def get_progress_config(task: str):
    """Progress bar configuration."""
    if task == "architecture":
        return {"weights": {"manager": 10, "security": 30, "team_lead": 60, "judge": 80, "refiner": 70, "end": 100}}
    elif task == "diagrams":
        return {"weights": {"visuals": 30, "fix_diagram": 60, "validator": 90, "end": 100}}
    elif task == "code":
        return {"weights": {"scaffold": 80, "end": 100}}
    return {"weights": {}}

# ==========================================
# ⚙️ SIDEBAR
# ==========================================
with st.sidebar:
    st.title("⚙️ Studio Settings")
    
    # LLM Config
    provider = st.selectbox("LLM Provider", ["openai", "gemini", "claude", "ollama"], index=1)
    st.session_state["project_state"]["provider"] = provider
    
    api_key = st.text_input("API Key", type="password", value=st.session_state.get("api_key", ""))
    st.session_state["api_key"] = api_key
    

    # Knowledge Base
    st.divider()
    st.subheader("📚 Knowledge Base")
    uploaded_kb = st.file_uploader("Upload Company Standards", type=["pdf", "txt"])
    if uploaded_kb:
        res = knowledge.ingest_upload(uploaded_kb)
        st.toast(res)
    
    # Snapshots
    st.divider()
    snapshots = list_snapshots()
    snapshot_count = len(snapshots)
    st.subheader("📂 Snapshots")
    selected_snap = st.selectbox(f"Select from {snapshot_count} available snapshots",  snapshots)
    
    col_load, col_del = st.columns([1, 1])
    
    with col_load:
        if selected_snap != None and st.button("Load"):
            try:
                data = load_snapshot(selected_snap)
                # Merge loaded data into session state
                st.session_state["project_state"].update(data)
                import pdb; pdb.set_trace()
                if data.get("provider", ""):
                    st.session_state["provider"] = data["provider"]
                st.rerun()
            except Exception as e:
                st.error(f"Load failed: {e}")
    with col_del:
         if selected_snap != None and st.button("Delete"):
            if delete_snapshot(selected_snap):
                st.toast(f"Deleted {selected_snap}")
                time.sleep(1)
                st.rerun()



# ==========================================
# 🚀 MAIN APP LAYOUT
# ==========================================

# 1. Header & Estimation
col_title, col_metrics, buttons = st.columns([3, 1, 0.5])
with col_title:
    st.title("🤖 AI Architect Studio")
with col_metrics:
    tokens = st.session_state["project_state"]["total_tokens"]
    cost_str = calculate_cost(tokens, provider)
    st.metric(label="Estimated Cost", value=cost_str, delta=f"{tokens} Tokens")


with buttons:
    if st.button("💾 Save Progress", use_container_width=True):
        if st.session_state["project_state"].get("hld"):
            fname = save_snapshot(st.session_state["project_state"]["project_name"], st.session_state["project_state"])
            if fname: st.toast(f"Saved: {fname}", icon="✅")
        else:
            st.toast("Nothing to save yet.", icon="⚠️")
    if st.button("🗑️ Clear Progress", use_container_width=True):
        st.session_state["project_state"] = {
            "hld": None, "lld": None, "scaffold": None, 
            "diagram_code": None, "diagram_path": None, 
            "logs": [], "total_tokens": 0, "provider": provider, 
            "user_request": "", "project_name": "NewProject"
        }
        st.rerun()


# 2. Input Area
with st.container():
    p_name = st.text_input("Project Name", placeholder="Provider Project Name Identifier...", value=st.session_state["project_state"]["project_name"])
    st.session_state["project_state"]["project_name"] = p_name
    
    req_text = st.text_area("Requirements", height=100, placeholder="Describe your system...", value=st.session_state["project_state"]["user_request"])
    st.session_state["project_state"]["user_request"] = req_text
    
    if st.session_state["project_state"]["lld"] and st.session_state["project_state"]["hld"]:
        button_label = "Regenerate"
    else:
        button_label = "Generate"

    if st.button(f"🚀 {button_label} Architecture", type="primary"):
        if not api_key and provider != "ollama":
            st.error("API Key required.")
        else:
            st.session_state["running_task"] = "architecture"
            st.rerun()

# 3. Dynamic Progress Bar (Only visible when running)
if st.session_state["running_task"]:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Prepare Graph Input
    initial_state = st.session_state["project_state"].copy()
    initial_state["task"] = st.session_state["running_task"]
    initial_state["api_key"] = api_key
    initial_state["provider"] = provider
    
    # Stream Graph
    try:
        current_weights = get_progress_config(st.session_state["running_task"])["weights"]
        
        for event in app_graph.stream(initial_state):
            for node, update in event.items():
                # Update Session State with results
                st.session_state["project_state"].update(update)
                
                # Update UI Progress
                prog = min(current_weights.get(node, 0), 95)
                progress_bar.progress(prog)
                status_text.markdown(f"**Processing:** {node.replace('_', ' ').capitalize()}...")
        
        progress_bar.progress(100)
        status_text.success(f"{st.session_state['running_task'].capitalize()} Complete!")
        time.sleep(1) 
    except Exception as e:
        st.error(f"Workflow failed: {e}")
    
    # Cleanup and Refresh
    st.session_state["running_task"] = None
    st.rerun()

st.divider()

# 4. Artifact Tabs
t_hld, t_lld, t_code, t_diag = st.tabs(["🏛️ HLD", "💻 LLD", "🛠️ Code", "📂 Diagrams"])

# --- HLD Tab ---
with t_hld:
    if st.session_state["project_state"]["hld"]:
        display_hld(st.session_state["project_state"]["hld"], st.container())
    else:
        st.info("No High-Level Design generated yet.")

# --- LLD Tab ---
with t_lld:
    if st.session_state["project_state"]["lld"]:
        display_lld(st.session_state["project_state"]["lld"], st.container())
    else:
        st.info("No Low-Level Design generated yet.")

# --- Code Tab ---
with t_code:
    col_act, col_view = st.columns([1, 4])
    with col_act:
        if st.session_state["project_state"]["lld"]:
            if st.button("⚡ Generate Code"):
                st.session_state["running_task"] = "code"
                st.rerun()
        else:
            st.button("⚡ Generate Code", disabled=True, help="Requires LLD first")

    if st.session_state["project_state"]["scaffold"]:
        st.success(f"Generated {len(st.session_state['project_state']['scaffold'].starter_files)} files.")
        for f in st.session_state["project_state"]["scaffold"].starter_files:
            with st.expander(f"📄 {f.filename}"):
                st.code(f.content)
        
        # Download
        output_dir = f"./output/{st.session_state['project_state']['project_name']}"
        generate_scaffold(st.session_state["project_state"]["scaffold"], output_dir=output_dir)
        shutil.make_archive(output_dir, 'zip', output_dir)
        with open(f"{output_dir}.zip", "rb") as f:
            st.download_button("⬇️ Download ZIP", f, file_name=f"{st.session_state['project_state']['project_name']}.zip")
    else:
        st.write("No code generated yet. Requires HLD and LLD.")

with t_diag:
    col_act_d, col_view_d = st.columns([1, 4])
    
    # 1. Action Column (Buttons)
    with col_act_d:
        # Only allow generation if HLD exists (Prerequisite)
        if st.session_state["project_state"]["hld"]:
            # Change label based on whether diagrams already exist
            has_diagrams = st.session_state["project_state"]["diagram_code"] is not None
            btn_label_d = "🎨 Regenerate Diagrams" if has_diagrams else "🎨 Generate Diagrams"
            
            if st.button(btn_label_d, use_container_width=True):
                st.session_state["running_task"] = "diagrams"
                st.rerun()
        else:
            # Show disabled button if HLD is missing
            st.button("🎨 Generate Diagrams", disabled=True, use_container_width=True, help="Requires HLD first")

    # 2. View Column (Render Mermaid)
    with col_view_d:
        diagram_code = st.session_state["project_state"]["diagram_code"]
        
        if diagram_code:
            st.subheader("System Context")
            render_mermaid(diagram_code.system_context)
            
            st.subheader("Container Diagram")
            render_mermaid(diagram_code.container_diagram)
            
            st.subheader("Data Flow")
            render_mermaid(diagram_code.data_flow)
        else:
            st.info("No diagrams generated yet.")