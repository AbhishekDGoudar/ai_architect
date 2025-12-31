import streamlit as st
import pandas as pd
import shutil
import os
import time
from datetime import datetime
import agents
import re

from graph import app_graph
from schemas import HighLevelDesign, LowLevelDesign
from storage import save_snapshot, list_snapshots, load_snapshot, delete_snapshot
from tools import generate_scaffold, download_multiple_books, books_map
from model_factory import get_llm
from callbacks import TokenMeter
from rag import KnowledgeEngine, WebKnowledgeEngine # Knowledge base engine
import streamlit.components.v1 as components
from io import StringIO
from pypdf import PdfReader
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

st.set_page_config(page_title="AI Architect Studio", layout="wide")

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
#  SESSION STATE INITIALIZATION
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

def get_priority_color(priority):
    if priority == "High":
        return "red"
    elif priority == "Medium":
        return "orange"
    return "blue"

# Check if the SQLite file exists
def check_sqlite_folder_and_file_exists() -> bool:
    """Check if the folder and SQLite file both exist. Returns True if both exist."""
    chroma_db_folder = './chroma_db'
    chroma_db_file = os.path.join(chroma_db_folder, 'sqlite3')
    if os.path.isdir(chroma_db_folder) or os.path.exists(chroma_db_file):
            return True  # Both the folder and file exist
    download_multiple_books() 
    return False 



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
            st.markdown("### 🧪 Traceability Matrix & Execution")
            st.caption("Verify requirements against test scenarios, execution steps, and expected outcomes.")
            st.divider()

            # Iterate through the Pydantic objects
            for index, test in enumerate(lld.test_traceability):
                
                # --- HEADER SECTION ---
                c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
                
                with c1:
                    # DOT NOTATION FIX: test.test_type instead of test.get('test_type')
                    st.subheader(f"TC-{index+1}: {test.test_type}")
                    st.markdown(f"**Requirement:** _{test.requirement}_")
                
                with c2:
                    # DOT NOTATION FIX
                    priority = test.test_priority
                    color = get_priority_color(priority)
                    st.markdown(f":{color}[**{priority} Priority**]")
                    
                with c3:
                    # DOT NOTATION FIX
                    st.markdown(f"**Owner:**\n{test.test_owner}")

                # --- DETAIL SECTION ---
                tab_overview, tab_execution, tab_data = st.tabs(["📝 Overview", "▶️ Execution Steps", "💾 Data & Env"])

                # TAB 1: OVERVIEW
                with tab_overview:
                    st.markdown(f"**Scenario:** {test.test_scenario}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.info(f"**Expected Result:**\n\n{test.expected_result}")
                    with col_b:
                        st.markdown("**Methodology:**")
                        st.code(test.test_methodology, language="text")

                # TAB 2: EXECUTION STEPS
                with tab_execution:
                    st.write("#### 🛠 Test Steps")
                    # DOT NOTATION FIX: test.test_steps
                    for i, step in enumerate(test.test_steps):
                        st.checkbox(step, key=f"step_{index}_{i}")
                    
                    st.divider()
                    
                    with st.expander("Verify Post-conditions"):
                        # DOT NOTATION FIX: test.test_postconditions
                        for condition in test.test_postconditions:
                            st.markdown(f"- {condition}")

                # TAB 3: DATA & ENVIRONMENT
                with tab_data:
                    d_col1, d_col2 = st.columns(2)
                    
                    with d_col1:
                        st.write("**Pre-conditions:**")
                        # DOT NOTATION FIX: test.test_preconditions
                        for pre in test.test_preconditions:
                            st.markdown(f"- ✅ {pre}")
                    
                    with d_col2:
                        st.write("**Test Data Requirements:**")
                        # DOT NOTATION FIX: test.test_data_requirements
                        for data_req in test.test_data_requirements:
                            if "JSON" in data_req or "key" in data_req.lower():
                                st.code(data_req, language="json")
                            else:
                                st.info(data_req)


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
    provider = st.selectbox(
        "LLM Provider", 
        ["openai", "gemini", "claude"],
        index=["openai", "gemini", "claude"].index(st.session_state["project_state"]["provider"])  # Set the default index from session state
    )
    st.session_state["project_state"]["provider"] = provider
    
    api_key = st.text_input("API Key", type="password", value=st.session_state.get("api_key", ""))
    st.session_state["api_key"] = api_key
    





# ==========================================
# 1. RENDER MAIN APP (Architect Studio)
# ==========================================
def render_main_app():
    """
    Main application layout with state synchronization.
    """
    # Ensure project state exists
    if "project_state" not in st.session_state:
        st.session_state["project_state"] = {}

    # --- Header & Metrics ---
    col_title, col_metric = st.columns([2, 1])
    with col_title:
        st.title("AI Architect Studio")
        st.caption("AI Architect Studio transforms weeks of planning into minutes by standardizing architecture and generating base code. We designed this to support your product managers and engineers. The platform employs specialized AI agents acting as a virtual software team to analyze and align outputs with your specific requirements. While the tool delivers speed, human judgment remains essential for final validation.")

    with col_metric:
        tokens = st.session_state["project_state"].get("total_tokens", 0)
        # Fallback if provider not set
        prov = st.session_state["project_state"].get("provider", "openai")
        try:
            cost_str = calculate_cost(tokens, prov)
        except:
            cost_str = "$0.00"
        st.metric(label="Current Project Cost", value=cost_str, delta=f"{tokens:,} Tokens")

    # --- Action Toolbar ---
    st.markdown("---")
    col_save, col_clear, col_snap_manager = st.columns([1, 1, 2])
    with col_save:
        if st.button("Save Progress", use_container_width=True, type="primary"):
            state = st.session_state["project_state"]
            if state.get("hld"):
                save_snapshot(state.get("project_name", "Untitled"), state)
                st.toast(f"Project saved successfully")
            else:
                st.warning("No architecture data found to save. Generate HLD first.")
    
    with col_clear:
        if st.button("Reset Project", use_container_width=True):
            st.session_state["project_state"] = {
                "hld": None, "lld": None, "scaffold": None, 
                "diagram_code": None, "diagram_path": None, 
                "logs": [], "total_tokens": 0, 
                "provider": prov, 
                "user_request": "", "project_name": "NewProject"
            }
            # Clear specific widget keys to prevent stale data
            if "req_input_main" in st.session_state: del st.session_state["req_input_main"]
            if "req_input_chat" in st.session_state: del st.session_state["req_input_chat"]
            st.rerun()

    with col_snap_manager:
        with st.popover("Manage Snapshots", use_container_width=True):
            snapshots = list_snapshots()
            if not snapshots:
                st.info("No saved snapshots available.")
            else:
                selected_snap = st.selectbox("Select Snapshot", snapshots)
                p_col_load, p_col_del = st.columns(2)
                with p_col_load:
                    if st.button("Load", use_container_width=True):
                        try:
                            data = load_snapshot(selected_snap)
                            st.session_state["project_state"].update(data)
                            st.toast(f"Snapshot loaded")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                with p_col_del:
                    if st.button("Delete", type="primary", disabled=True):
                        delete_snapshot(selected_snap)
                        st.rerun()

    # --- Configuration & Input Area ---
    with st.container(border=True):
        st.subheader("Project Configuration")
        
        # Initialization Check
        if "project_name" not in st.session_state["project_state"]:
             st.session_state["project_state"]["project_name"] = "MyGenAIApp"

        # Project Name
        p_name = st.text_input(
            "Project Identifier", 
            placeholder="Enter a unique name...", 
            value=st.session_state["project_state"]["project_name"]
        )
        st.session_state["project_state"]["project_name"] = p_name

        
        # --- SYNCHRONIZATION LOGIC (Main App) ---
        # 1. Define Callback: Syncs Widget -> Global State
        def sync_reqs_main():
            st.session_state["project_state"]["user_request"] = st.session_state["req_input_main"]

        # 2. Sync Global State -> Widget (Before Render)
        if "req_input_main" not in st.session_state:
            st.session_state["req_input_main"] = st.session_state["project_state"].get("user_request", "")
        
        # Force update from global state (handling updates from Chat Page)
        st.session_state["req_input_main"] = st.session_state["project_state"].get("user_request", "")

        req_text = st.text_area(
            "System Requirements", 
            height=200, 
            key="req_input_main", # Unique key for Main App
            on_change=sync_reqs_main, 
            placeholder="Briefly describe your system here, or click 'Brainstorm' to upload docs and refine..."
        )
        
        # --- NEW NAVIGATION BUTTON ---
        col_brainstorm, col_generate = st.columns([1, 1])
        
        with col_brainstorm:
            if st.button("✨ Brainstorm & Fix Requirements", use_container_width=True):
                st.session_state["active_page"] = "Chat Assistant"
                st.rerun()
                
        with col_generate:
            button_label = "Regenerate Architecture" if st.session_state["project_state"].get("hld") else "Generate Architecture"
            if st.button(button_label, type="primary", use_container_width=True):
                st.session_state["running_task"] = "architecture"
                st.rerun()
        
        st.caption("Tip: Use 'Brainstorm' to upload documents or let AI refine your ideas.")

    st.divider()

    # --- Artifact Output Tabs ---
    st.subheader("Project Artifacts")
    t_hld, t_lld, t_code, t_diag = st.tabs(["High Level Design", "Low Level Design", "Source Code", "System Diagrams"])

    with t_hld:
        if st.session_state["project_state"]["hld"]:
            display_hld(st.session_state["project_state"]["hld"], st.container())
        else:
            st.info("No HLD generated yet.")

    with t_lld:
        if st.session_state["project_state"]["lld"]:
            display_lld(st.session_state["project_state"]["lld"], st.container())
        else:
            st.info("No LLD generated yet.")

    with t_code:
        if st.session_state["project_state"]["scaffold"]:
            st.success(f"Generated {len(st.session_state['project_state']['scaffold'].starter_files)} files.")
            for f in st.session_state["project_state"]["scaffold"].starter_files:
                with st.expander(f.filename): st.code(f.content)
            
            output_dir = f"./output/{st.session_state['project_state']['project_name']}"
            generate_scaffold(st.session_state["project_state"]["scaffold"], output_dir=output_dir)
            shutil.make_archive(output_dir, 'zip', output_dir)
            with open(f"{output_dir}.zip", "rb") as f:
                st.download_button("Download ZIP", f, file_name=f"{st.session_state['project_state']['project_name']}.zip")
        elif st.session_state["project_state"]["lld"]:
            if st.button("Generate Code"):
                st.session_state["running_task"] = "code"
                st.rerun()
        else:
            st.warning("Generate LLD first.")

    with t_diag:
        if st.session_state["project_state"]["diagram_code"]:
            render_mermaid(st.session_state["project_state"]["diagram_code"].system_context)
            render_mermaid(st.session_state["project_state"]["diagram_code"].container_diagram)
            render_mermaid(st.session_state["project_state"]["diagram_code"].data_flow)
        elif st.session_state["project_state"]["hld"]:
             if st.button("Generate Diagrams"):
                st.session_state["running_task"] = "diagrams"
                st.rerun()
        else:
            st.info("No diagrams available.")


# ==========================================
# 2. RENDER CHAT PAGE (Brainstorming)
# ==========================================
def render_chat_page():
    """
    Chat Interface with File Upload, Sync, and Auto-Update.
    """
    # ==========================================
    # 🟢 SYNC LOGIC (MUST BE AT TOP)
    # ==========================================
    # 1. Ensure Widget Key Exists
    if "req_input_chat" not in st.session_state:
        st.session_state["req_input_chat"] = st.session_state["project_state"].get("user_request", "")

    # 2. Sync Global State -> Widget State (Pre-render)
    # This captures changes made in the Main App or via AI Auto-Update on the previous run
    current_global = st.session_state["project_state"].get("user_request", "")
    if st.session_state["req_input_chat"] != current_global:
        st.session_state["req_input_chat"] = current_global

    # 3. Define Callback: Syncs Widget -> Global State (When user types manually)
    def sync_reqs_chat():
        st.session_state["project_state"]["user_request"] = st.session_state["req_input_chat"]

    # ==========================================
    # 🎨 UI RENDERING
    # ==========================================
    col_chat, col_controls = st.columns([2, 1], gap="medium")

    # --- RIGHT COLUMN: Controls ---
    with col_controls:
        st.subheader("🛠️ Context & Assets")
        
        # 1. FILE UPLOADER
        with st.expander("📂 Upload Documents", expanded=True):
            uploaded_file = st.file_uploader(
                "Attach specs, PDFs, or docs", 
                type=['pdf', 'txt', 'md', 'json'],
                key="chat_doc_uploader"  # Unique Key to prevent collisions
            )
            
            if uploaded_file:
                try:
                    content = ""
                    if uploaded_file.name.lower().endswith('.pdf'):
                        reader = PdfReader(uploaded_file)
                        content = "\n".join([p.extract_text() for p in reader.pages])
                    else:
                        content = StringIO(uploaded_file.getvalue().decode("utf-8")).read()
                    
                    if content:
                        btn_label = f"➕ Append {uploaded_file.name}"
                        if st.button(btn_label, use_container_width=True):
                            append_str = f"\n\n--- [FILE: {uploaded_file.name}] ---\n{content}\n----------------\n"
                            
                            # UPDATE GLOBAL STATE FIRST
                            new_text = st.session_state["project_state"].get("user_request", "") + append_str
                            st.session_state["project_state"]["user_request"] = new_text
                            
                            st.toast("File appended!")
                            # RERUN IMMEDIATELY
                            # The Sync Logic at the top of the NEXT run will update the widget key.
                            st.rerun()
                except Exception as e:
                    st.error(f"Error reading file: {e}")

        st.caption("Edit requirements below or ask AI to update them.")
        
        # 2. REQUIREMENTS EDITOR
        new_reqs = st.text_area(
            "Current Requirements",
            height=400,
            key="req_input_chat", # Unique Key for Chat Page
            on_change=sync_reqs_chat
        )
        
        st.divider()
        
        # 3. SAVE & RETURN
        if st.button("💾 Save & Return to Studio", type="primary", use_container_width=True):
            # Final sync
            st.session_state["project_state"]["user_request"] = new_reqs
            st.session_state["active_page"] = "Architect Studio"
            st.toast("Requirements saved!")
            time.sleep(0.5) 
            st.rerun()

    # --- LEFT COLUMN: Chat ---
    with col_chat:
        c_head, c_mode = st.columns([1,1])
        with c_head: st.subheader("💬 AI Assistant")
        with c_mode:
            mode = st.segmented_control("Mode", ["🔍 Refine", "💡 Brainstorm"], default="🔍 Refine", label_visibility="collapsed")

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = [AIMessage(content="Hello! I can analyze your requirements or help you brainstorm. Upload a doc on the right to get started!")]

        # Chat History
        chat_container = st.container(height=550)
        with chat_container:
            for msg in st.session_state["chat_history"]:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                with st.chat_message(role):
                    clean_content = re.sub(r'<UPDATE_REQ>.*?</UPDATE_REQ>', '', msg.content, flags=re.DOTALL).strip()
                    if clean_content: st.markdown(clean_content)
                    if "<UPDATE_REQ>" in msg.content: st.info("*Requirements updated*")

        # Chat Input
        if prompt := st.chat_input("Ex: 'Analyze the uploaded PDF for security gaps'"):
            with chat_container: st.chat_message("user").markdown(prompt)
            st.session_state["chat_history"].append(HumanMessage(content=prompt))

            # Prepare Context
            reqs_text = st.session_state["project_state"].get("user_request", "")
            hld_context = ""
            if st.session_state["project_state"].get("hld"):
                hld_context = f"\n[Existing HLD]:\n{st.session_state['project_state']['hld'].business_context}\n"

            context_str = f"Project: {st.session_state['project_state'].get('project_name')}\nREQS:\n{reqs_text}\n{hld_context}"

            # Prompt
            base_instruction = (
                "You are a Chief Architect. You can update requirements directly.\n"
                "If user asks to change/add/refine reqs: OUTPUT <UPDATE_REQ> new full text </UPDATE_REQ>.\n"
                "If user asks questions, just answer.\n"
            )
            
            if mode == "🔍 Refine":
                sys_p = f"{base_instruction}\nMODE: REFINE. Check for gaps (NFRs, Security, Scale).\nCONTEXT:\n{context_str}"
            else:
                sys_p = f"{base_instruction}\nMODE: BRAINSTORM. Be creative.\nCONTEXT:\n{context_str}"

            with chat_container:
                with st.chat_message("assistant"):
                    api_key = st.session_state.get("api_key")
                    provider = st.session_state["project_state"].get("provider", "openai")
                    
                    if not api_key:
                        st.error("No API Key found.")
                    else:
                        should_rerun = False
                        try:
                            llm = get_llm(provider=provider, api_key=api_key)
                            messages = [SystemMessage(content=sys_p)] + st.session_state["chat_history"][-6:]
                            full_response = st.write_stream(llm.stream(messages))
                            
                            # Auto-Update Logic
                            match = re.search(r'<UPDATE_REQ>(.*?)</UPDATE_REQ>', full_response, re.DOTALL)
                            if match:
                                new_text = match.group(1).strip()
                                # Update Global State
                                st.session_state["project_state"]["user_request"] = new_text
                                should_rerun = True
                            
                            st.session_state["chat_history"].append(AIMessage(content=full_response))
                        except Exception as e: st.error(f"Error: {e}")
                        
                        if should_rerun: 
                            st.rerun()


def run_global_workflow_if_needed():
    """
    Checks if a task is running. If so, executes the graph and renders 
    a progress bar at the top of the app, regardless of which page is active.
    """
    if st.session_state.get("running_task"):
        # Create a container at the very top
        with st.container():
            st.info(f"🚀 {st.session_state['running_task'].capitalize()} in progress...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Prepare State
            initial_state = st.session_state["project_state"].copy()
            initial_state["task"] = st.session_state["running_task"]
            initial_state["api_key"] = st.session_state.get("api_key")
            initial_state["provider"] = st.session_state["project_state"].get("provider")
            
            try:
                # Get Config
                current_weights = get_progress_config(st.session_state["running_task"]).get("weights", {})
                
                # Run Graph
                for event in app_graph.stream(initial_state):
                    for node, update in event.items():
                        st.session_state["project_state"].update(update)
                        
                        # Update Progress
                        prog = min(current_weights.get(node, 0), 95)
                        progress_bar.progress(prog)
                        status_text.markdown(f"**Processing:** {node.replace('_', ' ').title()}...")
                
                progress_bar.progress(100)
                status_text.success("Workflow completed successfully!")
                time.sleep(1.5)
                
                # Clear the running task
                st.session_state["running_task"] = None
                st.rerun()
                
            except Exception as e:
                st.error(f"Workflow execution failed: {e}")
                st.session_state["running_task"] = None


def render_knowledge_page():
    """
    Dedicated page for managing Knowledge Base and RAG Chat.
    """
    st.title("📚 Knowledge Studio")
    st.caption("Ingest engineering standards, architectural patterns, and legacy documentation here.")

    # --- 1. CONFIGURATION & INGESTION ---
    with st.expander("⚙️ Knowledge Base Management", expanded=False):
        
        api_key = st.session_state.get("api_key")
        
        if not api_key:
            st.warning("Please configure your OpenAI API Key in the settings sidebar to use the Knowledge Engine.")
        else:
            kb = KnowledgeEngine(api_key)
            
            c1, c2 = st.columns(2)
            
            # Option A: Upload
            with c1:
                st.markdown("##### 📤 Upload File")
                uploaded_kb = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"], key="kb_uploader")
                if uploaded_file := uploaded_kb:
                    if st.button("Ingest Uploaded File"):
                        with st.spinner("Indexing..."):
                            res = kb.ingest_upload(uploaded_file)
                            st.success(res)
            
            # Option B: Bulk Ingest
            with c2:
                if check_sqlite_folder_and_file_exists():
                        render_list(books_map.keys(), "The default books in the knowledge base are")
                else:
                    st.markdown("##### 🏗️ Bulk Ingest")
                    if st.button("Ingest Local Directory"):
                        st.caption(f"Scans local folder: `./knowledge_base`")
                        with st.spinner("Processing directory..."):
                            res = kb.ingest_directory()
                            st.success(res)

    st.divider()

    # --- 2. RAG CHATBOT ---
    st.subheader("🧠 Consult the Library")
    st.caption("Chat specifically with your ingested documents.")

    # Initialize KB Chat History
    if "kb_chat_history" not in st.session_state:
        st.session_state["kb_chat_history"] = [
            AIMessage(content="Hello! I have access to your uploaded architectural standards. What do you need to look up?")
        ]

    # Display History
    for msg in st.session_state["kb_chat_history"]:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(msg.content)

    # Handle Input
    if prompt := st.chat_input("Ex: 'What is our standard for retry policies in microservices?'"):
        
        # 1. User Message
        st.session_state["kb_chat_history"].append(HumanMessage(content=prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Assistant Response
        with st.chat_message("assistant"):
            api_key = st.session_state.get("api_key")
            provider = st.session_state["project_state"].get("provider", "openai")
            
            if not api_key:
                st.error("API Key missing.")
            else:
                try:
                    kb = KnowledgeEngine(api_key) # Re-init is cheap, connection is pooled
                    llm = get_llm(provider=provider, api_key=api_key)
                    
                    # A. Retrieval
                    with st.spinner("Searching knowledge base..."):
                        context_str = kb.search(prompt, k=5, score_threshold=0.4)
                    
                    # B. Augmented Prompt
                    if context_str:
                        system_msg = (
                            "You are an expert Technical Librarian.\n"
                            "Answer the user's question using ONLY the context provided below.\n"
                            "If the answer is not in the context, state that you cannot find it in the knowledge base.\n"
                            "Cite the source filename if available.\n\n"
                            f"--- CONTEXT ---\n{context_str}"
                        )
                        display_prefix = "📚 *Found relevant documents:*\n"
                    else:
                        system_msg = (
                            "You are an expert Technical Architect.\n"
                            "The user searched the knowledge base but NO RELEVANT DOCUMENTS were found.\n"
                            "Answer the question using your general knowledge, but explicitly state that this is NOT from the company knowledge base."
                        )
                        display_prefix = "⚠️ *No relevant documents found in KB. Answering from general knowledge:*\n"

                    # C. Generation
                    messages = [SystemMessage(content=system_msg)] + st.session_state["kb_chat_history"][-4:]
                    
                    # Stream response
                    full_response = st.write_stream(llm.stream(messages))
                    
                    # Save to history
                    st.session_state["kb_chat_history"].append(AIMessage(content=full_response))
                    
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# 3. MAIN ROUTER
# ==========================================
def main():
    # 1. Initialize Navigation State
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "Architect Studio"

    # 2. Global Workflow Runner
    run_global_workflow_if_needed()

    # 3. Sidebar Navigation
    with st.sidebar:
        st.title("🧭 Navigation")
        
        
        # Sync selection
        navs = ["Architect Studio"]
        if provider == "openai":
            navs.append("Knowledge Studio")

        # DYNAMICALLY ADD CHAT if it is the active page
        if st.session_state["active_page"] == "Chat Assistant":
            navs.append("Chat Assistant") 

        # Now st.radio logic is simple and bug-free:
        try:
            nav_index = navs.index(st.session_state["active_page"])
        except ValueError:
            nav_index = 0 

        selected_page = st.radio("Go to", navs, index=nav_index)

        if selected_page != st.session_state["active_page"]:
            st.session_state["active_page"] = selected_page
            st.rerun()
        st.divider()
        # Keep your Settings/API Key inputs here...

    # 4. Router Logic
    if st.session_state["active_page"] == "Architect Studio":
        render_main_app()
    elif provider == "openai" and st.session_state["active_page"] == "Knowledge Studio":
        render_knowledge_page()
    elif st.session_state["active_page"] == "Chat Assistant":
        render_chat_page()

if __name__ == "__main__":
    main()

    