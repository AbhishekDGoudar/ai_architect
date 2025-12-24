from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

# ==========================================
# 📚 SHARED MODELS
# ==========================================

class Citation(BaseModel):
    description: str = Field(description="Context or claim being supported.")
    source: str = Field(description="Reference source (Book title, URL, Standard).")

class TechStackItem(BaseModel):
    layer: str = Field(description="The architectural layer (e.g., 'Frontend').")
    technology: str = Field(description="The chosen technology (e.g., 'React').")
    recommended_version: Optional[str] = None
    rationale: Optional[str] = None

class DataOwnerItem(BaseModel):
    component: str = Field(description="The service name.")
    data_owned: str = Field(description="Entities owned (e.g., 'User Profile').")

class StorageChoiceItem(BaseModel):
    component: str = Field(description="The service name.")
    technology: str = Field(description="Storage technology (e.g., 'PostgreSQL').")

# ==========================================
# 🧠 SECTION 1: HIGH-LEVEL DESIGN (HLD)
# ==========================================

class BusinessContext(BaseModel):
    version: str
    change_log: List[str]
    problem_statement: str
    business_goals: List[str]
    in_scope: List[str]
    out_of_scope: List[str]
    assumptions_constraints: List[str]
    non_goals: List[str]
    stakeholders: List[str]

    @field_validator('business_goals', 'stakeholders')
    def list_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('This list cannot be empty. Provide at least one item.')
        return v

class ArchitectureDiagrams(BaseModel):
    # CHANGED: Updated descriptions to request Mermaid syntax
    system_context: str = Field(description="Mermaid.js code (graph TD or C4Context) for System Context.")
    container_diagram: str = Field(description="Mermaid.js code (graph TD with subgraphs) for Container Diagram.")
    data_flow: str = Field(description="Mermaid.js code (sequenceDiagram) for Data Flow.")

    @field_validator('system_context', 'container_diagram')
    def code_must_be_valid(cls, v):
        if "Diagram" not in v:
            raise ValueError("Code must use the 'diagrams' library.")
        return v

# HLD Additions
class LayerTechRationale(BaseModel):
    layer: str = Field(description="Name of the architecture layer, e.g., 'Frontend', 'Backend'.")
    technology: str = Field(description="Technology used in this layer.")
    rationale: str = Field(description="Reason for choosing this technology over alternatives.")
    tradeoffs: str = Field(description="Key trade-offs considered for this layer's technology.")

class EventFlowDescription(BaseModel):
    description: str = Field(description="Textual description of async/event-driven communication patterns.")
    components_involved: List[str] = Field(description="List of components involved in the flow.")
    event_types: List[str] = Field(description="Types of events/messages being exchanged.")

class KPIMetric(BaseModel):
    goal: str = Field(description="Business goal or objective this KPI maps to.")
    metric: str = Field(description="Quantitative or qualitative metric for tracking success.")
    target_value: Optional[str] = Field(description="Target value or threshold, if applicable.")

class ArchitectureOverview(BaseModel):
    style: str = Field(description="Architecture style (e.g., 'Microservices', 'Event-Driven', 'Monolith').")
    external_interfaces: List[str]
    user_stories: List[str]
    tech_stack: List[TechStackItem]
    diagrams: List[ArchitectureDiagrams] = None
    layer_tech_rationale: List[LayerTechRationale] = Field(default_factory=list, description="Rationale for each layer's technology.")
    event_flows: List[EventFlowDescription] = Field(default_factory=list, description="Description of event-driven flows between components.")
    kpis: List[KPIMetric] = Field(default_factory=list, description="KPIs mapped to business goals.")

    @field_validator('tech_stack')
    def tech_stack_check(cls, v):
        if len(v) < 2:
            raise ValueError("Tech stack is too thin. Define at least 2 layers.")
        return v

class ComponentSpec(BaseModel):
    name: str
    responsibility: str
    design_patterns: List[str]
    communication_protocols: List[str]
    sync_async_boundaries: str
    trust_boundaries: str
    component_dependencies: List[str]
    component_metrics: List[str]
    component_ownership: str

class DataArchitecture(BaseModel):
    data_ownership_map: List[DataOwnerItem]
    storage_choices: List[StorageChoiceItem]
    data_classification: str = Field(description="e.g., 'Public', 'Internal', 'Confidential', 'Restricted'")
    consistency_model: str = Field(description="e.g., 'Strong', 'Eventual', 'Causal'")
    data_retention_policy: str
    data_backup_recovery: str
    schema_evolution_strategy: str

class IntegrationStrategy(BaseModel):
    public_apis: List[str]
    internal_apis: List[str]
    api_gateway_strategy: str
    api_documentation: str
    contract_strategy: str = Field(description="e.g., 'OpenAPI', 'Protobuf', 'GraphQL'")
    versioning_strategy: str
    backward_compatibility_plan: str

class NFRs(BaseModel):
    scalability_plan: str
    availability_slo: str
    latency_targets: str
    security_requirements: List[str]
    reliability_targets: str
    maintainability_plan: str
    cost_constraints: str
    load_testing_strategy: str

class SecurityCompliance(BaseModel):
    threat_model_summary: str
    authentication_strategy: str
    authorization_strategy: str
    secrets_management: str
    data_encryption_at_rest: str
    data_encryption_in_transit: str
    auditing_mechanisms: str
    compliance_certifications: List[str]

class ReliabilityResilience(BaseModel):
    failover_strategy: str
    disaster_recovery_rpo_rto: str
    self_healing_mechanisms: str
    retry_backoff_strategy: str
    circuit_breaker_policy: str

class ObservabilityStrategy(BaseModel):
    logging_strategy: str
    metrics_collection: List[str]
    tracing_strategy: str
    alerting_rules: List[str]

class DeploymentOperations(BaseModel):
    cloud_provider: str
    deployment_model: str = Field(description="e.g., 'Serverless', 'Containers', 'VMs', 'On-Prem'")
    cicd_pipeline: str
    deployment_strategy: str = Field(description="e.g., 'Blue-Green', 'Canary', 'Rolling'")
    feature_flag_strategy: str
    rollback_strategy: str
    operational_monitoring: str
    git_repository_management: str

class DesignDecisions(BaseModel):
    patterns_used: List[str]
    tech_stack_justification: str
    trade_off_analysis: str
    rejected_alternatives: List[str]

class HighLevelDesign(BaseModel):
    business_context: BusinessContext
    architecture_overview: ArchitectureOverview
    core_components: List[ComponentSpec]
    data_architecture: DataArchitecture
    integration_strategy: IntegrationStrategy
    nfrs: NFRs
    security_compliance: SecurityCompliance
    reliability_resilience: ReliabilityResilience
    observability: ObservabilityStrategy
    deployment_ops: DeploymentOperations
    design_decisions: DesignDecisions
    citations: List[Citation]

# ==========================================
# 🧠 SECTION 2: LOW-LEVEL DESIGN (LLD)
# ==========================================

class MethodDetail(BaseModel):
    method_name: str = Field(description="Name of the method/function.")
    purpose: str = Field(description="Short description of what this method does.")
    input_params: List[str] = Field(description="List of input parameters and types.")
    output: str = Field(description="Expected output or return type.")
    algorithm_summary: str = Field(description="Brief description of the core logic/algorithm.")

class DataAccessPattern(BaseModel):
    entity: str = Field(description="Entity or table being accessed.")
    pattern_description: str = Field(description="How data is typically accessed, queried, or updated.")
    example_queries: List[str] = Field(default_factory=list, description="Optional example queries illustrating usage.")
    lifecycle_notes: str = Field(description="Lifecycle considerations for this data (e.g., retention, archival).")

class FailureHandlingFlow(BaseModel):
    component: str = Field(description="Component name.")
    flow_description: str = Field(description="Step-by-step failure handling flow.")
    retry_strategy: str = Field(description="Retry/backoff strategy for failures.")
    fallback_mechanisms: str = Field(description="Fallback or mitigation strategies when retries fail.")

class LoadBenchmarkTarget(BaseModel):
    component: str = Field(description="Component/service name.")
    expected_load: str = Field(description="Expected concurrent requests, transactions per second, or data volume.")
    benchmark_metric: str = Field(description="Performance metric used for benchmarking (latency, throughput, etc.)")
    target_value: str = Field(description="Target performance value for this component under expected load.")

class TestTraceability(BaseModel):
    requirement: str = Field(description="Requirement or business goal being tested.")
    test_case_ids: List[str] = Field(description="IDs of test cases validating this requirement.")
    coverage_status: str = Field(description="Coverage status (e.g., full, partial, missing).")

class InternalComponentDesign(BaseModel):
    component_name: str
    class_structure_desc: str
    module_boundaries: str
    interface_specifications: List[str]
    dependency_direction: str
    error_handling_local: str
    versioning: str
    security_considerations: str
    method_details: List[MethodDetail] = Field(default_factory=list, description="Detailed methods inside the component.")
    failure_handling_flows: List[FailureHandlingFlow] = Field(default_factory=list, description="Failure handling flows for this component.")
    load_benchmark_targets: List[LoadBenchmarkTarget] = Field(default_factory=list, description="Performance/load targets for this component.")

class APIEndpointDetail(BaseModel):
    endpoint: str
    method: str
    request_schema: str
    response_schema: str
    error_codes: List[str]
    rate_limiting_rule: str
    authorization_mechanism: str
    api_gateway_integration: str
    testing_strategy: str
    versioning_strategy: str

class DataModelDetail(BaseModel):
    entity: str
    attributes: List[str]
    indexes: List[str]
    constraints: List[str]
    validation_rules: List[str]
    foreign_keys: List[str]
    migration_strategy: str
    access_patterns: List[DataAccessPattern] = Field(default_factory=list, description="Typical access patterns for this data.")

class BusinessLogic(BaseModel):
    core_algorithms: str
    state_machine_desc: str
    concurrency_control: str
    async_processing_details: str

class ErrorHandlingStrategy(BaseModel):
    error_taxonomy: str
    custom_error_codes: List[str]
    retry_policies: str
    dlq_strategy: str
    exception_handling_framework: str

class SecurityImplementation(BaseModel):
    input_validation_rules: str
    auth_flow_diagram_desc: str
    token_management: str
    encryption_details: str

class PerformanceEng(BaseModel):
    caching_strategy: str
    cache_invalidation: str
    async_processing_desc: str
    load_balancing_strategy: str

class TestingStrategy(BaseModel):
    unit_test_scope: str
    integration_test_scope: str
    contract_testing_tools: str
    chaos_engineering_plan: str
    test_coverage_metrics: str

class OperationalReadiness(BaseModel):
    runbook_summary: str
    incident_response_plan: str
    monitoring_and_alerts: List[str]
    backup_recovery_procedures: str

class DocumentationGovernance(BaseModel):
    code_docs_standard: str
    api_docs_tooling: str
    adr_process: str
    document_review_process: str
    internal_vs_public_docs: str

class LowLevelDesign(BaseModel):
    detailed_components: List[InternalComponentDesign]
    api_design: List[APIEndpointDetail]
    data_model_deep_dive: List[DataModelDetail]
    business_logic: BusinessLogic
    consistency_concurrency: str
    error_handling: ErrorHandlingStrategy
    security_implementation: SecurityImplementation
    performance_engineering: PerformanceEng
    testing_strategy: TestingStrategy
    operational_readiness: OperationalReadiness
    documentation_governance: DocumentationGovernance
    test_traceability: List[TestTraceability] = Field(default_factory=list, description="Mapping of requirements to test cases and coverage.")
    citations: List[Citation]

# ==========================================
# 🛠️ SECTION 3: ARTIFACTS & METRICS
# ==========================================

class JudgeVerdict(BaseModel):
    is_valid: bool
    critique: str
    score: int
    hld_lld_mismatch: List[str]
    security_gaps: List[str]
    nfr_mismatches: List[str]
    diagram_issues: List[str]
    testing_coverage_gaps: List[str]
    iteration_recommendations: List[str]

class RefinedDesign(BaseModel):
    hld: HighLevelDesign
    lld: LowLevelDesign
    improvement_notes: str

class DiagramValidationResult(BaseModel):
    valid_syntax: bool
    missing_elements: List[str]
    invalid_elements: List[str]
    critique: str

# ==========================================
# 🏗️ SECTION 4: SCAFFOLDING & CODE GEN
# ==========================================

class FileSpec(BaseModel):
    filename: str = Field(description="Relative path, e.g., 'src/main.py'")
    content: str = Field(description="The actual code content.")

class ProjectStructure(BaseModel):
    project_name: str
    cookiecutter_url: Optional[str] = Field(description="URL to a cookiecutter template if applicable, else null.")
    starter_files: List[FileSpec] = Field(description="List of essential starter files (README, requirements.txt, main entrypoint).")
    
    @field_validator('starter_files')
    def has_files(cls, v):
        if not v:
            raise ValueError("Must generate at least one starter file (e.g., README).")
        return v
# ==========================================