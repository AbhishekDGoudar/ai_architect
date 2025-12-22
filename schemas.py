from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal

# ==========================================
# 🧠 SECTION 1: HIGH-LEVEL DESIGN (HLD)
# ==========================================

class BusinessContext(BaseModel):
    problem_statement: str
    business_goals: List[str]
    in_scope: List[str]
    out_of_scope: List[str]
    assumptions_constraints: List[str]
    non_goals: List[str]

class ArchitectureOverview(BaseModel):
    style: Literal["Microservices", "Event-Driven", "Monolith", "Hybrid", "Serverless"]
    system_context_diagram_desc: str = Field(description="Textual description of the system context")
    high_level_component_diagram_desc: str
    data_flow_desc: str
    external_dependencies: List[str]

class ComponentSpec(BaseModel):
    name: str
    responsibility: str
    communication_protocols: List[str] = Field(description="e.g. gRPC, REST, AMQP")
    sync_async_boundaries: str
    trust_boundaries: str

class DataArchitecture(BaseModel):
    data_ownership_map: Dict[str, str] = Field(description="Service -> Data Owned")
    storage_choices: Dict[str, str] = Field(description="Service -> Tech (e.g. UserSvc -> PostgreSQL)")
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
    availability_slo: str = Field(description="e.g. 99.99%")
    latency_targets: str = Field(description="e.g. p99 < 200ms")
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
    compliance_standards: List[str] = Field(description="e.g. GDPR, HIPAA, SOC2")

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

class ArchitectureDiagrams(BaseModel):
    """
    Dedicated model for PlantUML code.
    """
    system_context: str = Field(
        description="PlantUML code (@startuml ... @enduml) for System Context (Component Diagram)."
    )
    container_diagram: str = Field(
        description="PlantUML code (@startuml ... @enduml) for Containers using 'component' or 'package' syntax."
    )
    data_flow: str = Field(
        description="PlantUML code (@startuml ... @enduml) for Sequence Diagram showing critical path."
    )

class HighLevelDesign(BaseModel):
    """Items 1-11 of the Framework"""
    business_context: BusinessContext
    architecture_overview: ArchitectureOverview
    # 🆕 INTEGRATION POINT
    diagrams: Optional[ArchitectureDiagrams] = Field(description="Visual representations (PlantUML)")    
    core_components: List[ComponentSpec]
    data_architecture: DataArchitecture
    integration_strategy: IntegrationStrategy
    nfrs: NFRs
    security_compliance: SecurityCompliance
    reliability_resilience: ReliabilityResilience
    observability: ObservabilityStrategy
    deployment_ops: DeploymentOperations
    design_decisions: DesignDecisions

# ==========================================
# 🧠 SECTION 2: LOW-LEVEL DESIGN (LLD)
# ==========================================

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
    """Items 12-22 of the Framework"""
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

# --- Quality Control ---
class JudgeVerdict(BaseModel):
    is_valid: bool
    critique: str
    score: int