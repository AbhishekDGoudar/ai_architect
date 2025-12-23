from pydantic import BaseModel, Field
from typing import List, Literal

# ==========================================
# 📚 SHARED MODELS
# ==========================================

class Citation(BaseModel):
    description: str = Field(description="Context or claim being supported.")
    source: str = Field(description="Reference source (Book title, URL, Standard).")

class TechStackItem(BaseModel):
    layer: str = Field(description="The architectural layer (e.g., 'Frontend').")
    technology: str = Field(description="The chosen technology (e.g., 'React').")

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

class ArchitectureDiagrams(BaseModel):
    system_context: str = Field(description="Python code for System Context Diagram.")
    container_diagram: str = Field(description="Python code for Container Diagram.")
    data_flow: str = Field(description="Python code for Data Flow Diagram.")

class ArchitectureOverview(BaseModel):
    style: Literal["Microservices", "Event-Driven", "Monolith", "Hybrid", "Serverless"]
    system_context_diagram_desc: str
    high_level_component_diagram_desc: str
    data_flow_desc: str
    external_interfaces: List[str]
    user_stories: List[str]
    tech_stack: List[TechStackItem]

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
    data_classification: Literal["Public", "Internal", "Confidential", "Restricted"]
    consistency_model: Literal["Strong", "Eventual", "Causal"]
    data_retention_policy: str
    data_backup_recovery: str
    schema_evolution_strategy: str

class IntegrationStrategy(BaseModel):
    public_apis: List[str]
    internal_apis: List[str]
    api_gateway_strategy: str
    api_documentation: str
    contract_strategy: Literal["OpenAPI", "Protobuf", "GraphQL", "Thrift"]
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
    deployment_model: Literal["Serverless", "Containers", "VMs", "On-Prem"]
    cicd_pipeline: str
    deployment_strategy: Literal["Blue-Green", "Canary", "Rolling", "Recreate"]
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
    diagrams: ArchitectureDiagrams
    citations: List[Citation]

# ==========================================
# 🧠 SECTION 2: LOW-LEVEL DESIGN (LLD)
# ==========================================

class InternalComponentDesign(BaseModel):
    component_name: str
    class_structure_desc: str
    module_boundaries: str
    interface_specifications: List[str]
    dependency_direction: str
    error_handling_local: str
    versioning: str
    security_considerations: str

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