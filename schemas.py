from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal

# --- EXISTING HLD/LLD SCHEMAS (Simplified for brevity, assume full versions present) ---

class BusinessContext(BaseModel):
    problem_statement: str
    business_goals: List[str]
    in_scope: List[str]
    out_of_scope: List[str]
    assumptions_constraints: List[str]
    non_goals: List[str]

class ArchitectureOverview(BaseModel):
    style: Literal["Microservices", "Event-Driven", "Monolith", "Hybrid", "Serverless"]
    system_context_diagram_desc: str
    high_level_component_diagram_desc: str
    data_flow_desc: str
    external_dependencies: List[str]

class ComponentSpec(BaseModel):
    name: str
    responsibility: str
    communication_protocols: List[str]
    sync_async_boundaries: str
    trust_boundaries: str

class DataArchitecture(BaseModel):
    data_ownership_map: Dict[str, str]
    storage_choices: Dict[str, str]
    consistency_model: Literal["Strong", "Eventual", "Causal"]
    retention_archival_policy: str
    schema_evolution_strategy: str

class IntegrationStrategy(BaseModel):
    public_apis: List[str]
    internal_apis: List[str]
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

class SecurityCompliance(BaseModel):
    threat_model_summary: str
    authentication_strategy: str
    authorization_strategy: str
    secrets_management: str
    encryption_at_rest: str
    encryption_in_transit: str
    compliance_standards: List[str]

class ReliabilityResilience(BaseModel):
    failure_modes: List[str]
    retry_backoff_strategy: str
    circuit_breaker_policy: str
    disaster_recovery_rpo_rto: str

class ObservabilityStrategy(BaseModel):
    logging_standard: str
    metrics_to_track: List[str]
    tracing_strategy: str
    alerting_rules: List[str]

class DeploymentOperations(BaseModel):
    deployment_model: str
    env_strategy: str
    cicd_pipeline_desc: str
    feature_flag_strategy: str

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

# --- LLD SCHEMAS ---
class InternalComponentDesign(BaseModel):
    component_name: str
    class_structure_desc: str
    module_boundaries: str
    dependency_direction: str

class APIEndpointDetail(BaseModel):
    endpoint: str
    method: str
    request_schema: str
    response_schema: str
    error_codes: List[str]
    rate_limiting_rule: str

class DataModelDetail(BaseModel):
    entity: str
    attributes: List[str]
    indexes: List[str]
    constraints: List[str]

class BusinessLogic(BaseModel):
    core_algorithms: str
    state_machine_desc: Optional[str]
    concurrency_control: str

class ErrorHandlingStrategy(BaseModel):
    error_taxonomy: str
    retry_policies: str
    dlq_strategy: Optional[str]

class SecurityImplementation(BaseModel):
    auth_flow_diagram_desc: str
    token_lifecycle: str
    input_validation_rules: str

class PerformanceEng(BaseModel):
    caching_strategy: str
    cache_invalidation: str
    async_processing_desc: str

class TestingStrategy(BaseModel):
    unit_test_scope: str
    integration_test_scope: str
    contract_testing_tools: str
    chaos_testing_plan: Optional[str]

class OperationalReadiness(BaseModel):
    runbook_summary: str
    incident_response_plan: str
    rollback_strategy: str

class DocumentationGovernance(BaseModel):
    code_docs_standard: str
    api_docs_tooling: str
    adr_process: str

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

class JudgeVerdict(BaseModel):
    is_valid: bool
    critique: str
    score: int

# --- NEW: SCAFFOLDING & VISUALS ---

class FileSpec(BaseModel):
    filename: str
    content: str
    language: str

class ScaffoldingSpec(BaseModel):
    project_name: str
    cookiecutter_url: Optional[str] = Field(description="URL to a relevant cookiecutter template")
    folder_structure: List[str]
    files: List[FileSpec]
    setup_commands: List[str]

class DiagramCode(BaseModel):
    python_code: str = Field(description="Executable python code using 'diagrams' library.")
    filename: str = Field(default="architecture_diagram")

class RunMetrics(BaseModel):
    security_score: float
    security_reason: str
    red_team_issues: List[str]
    cost_estimate: float
    iterations: int