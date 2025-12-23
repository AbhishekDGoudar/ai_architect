from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any

# ==========================================
# 📚 SHARED MODELS
# ==========================================

class Citation(BaseModel):
    description: str = Field(description="Description of the decision or component")
    source: str = Field(description="Reference source (Book, Paper, Standard, URL)")

# ==========================================
# 🧠 SECTION 1: HIGH-LEVEL DESIGN (HLD)
# ==========================================

class BusinessContext(BaseModel):
    version: str = Field(
        description="Semantic or document version (e.g., v1.0, v2.1-draft). Used for traceability."
    )
    change_log: List[str] = Field(
        description=(
            "Chronological list of meaningful changes across iterations. "
            "Example: 'v1.1 – Updated scaling assumptions after traffic forecast review'."
        )
    )
    problem_statement: str = Field(
        description=(
            "Clear articulation of the business problem being solved. "
            "Describe current pain points, affected users, and why existing solutions are insufficient. "
            "Avoid proposing solutions here."
        )
    )
    business_goals: List[str] = Field(
        description=(
            "Concrete, measurable business outcomes. Each goal should be outcome-oriented, not feature-oriented. "
            "Example: 'Reduce checkout abandonment by 15%' instead of 'Improve checkout flow'."
        )
    )
    in_scope: List[str] = Field(
        description=(
            "Explicit list of what this system/design WILL cover. "
            "Used to prevent scope creep and misaligned expectations."
        )
    )
    out_of_scope: List[str] = Field(
        description=(
            "Explicit exclusions. Anything not listed here may be incorrectly assumed to be included."
        )
    )
    assumptions_constraints: List[str] = Field(
        description=(
            "Key assumptions and hard constraints shaping the design. "
            "Include regulatory, organizational, budget, time, and technical constraints. "
            "Example: 'Must operate only in EU regions due to GDPR'."
        )
    )
    non_goals: List[str] = Field(
        description=(
            "Things explicitly not optimized for. "
            "Example: 'Not optimized for offline-first usage in phase 1'."
        )
    )
    stakeholders: List[str] = Field(
        description=(
            "All relevant stakeholders with decision or review authority. "
            "Example: Product Owner, Security Team, Compliance Officer, External Partner."
        )
    )

# --- Diagram Container ---
class ArchitectureDiagrams(BaseModel):
    system_context: str = Field(
        description=(
            "Executable Python code (diagrams library) for the System Context Diagram. "
            "Shows users, external systems, and high-level boundaries."
        )
    )
    container_diagram: str = Field(
        description=(
            "Executable Python code for the Container Diagram. "
            "Shows services, databases, queues, and their interactions."
        )
    )
    data_flow: str = Field(
        description=(
            "Executable Python code for the Data Flow Diagram. "
            "Highlights data movement, trust boundaries, and sensitive data paths."
        )
    )

class ArchitectureOverview(BaseModel):
    style: Literal["Microservices", "Event-Driven", "Monolith", "Hybrid", "Serverless"] = Field(
        description=(
            "Primary architectural paradigm. If 'Hybrid' is chosen, "
            "the combination and rationale must be justified in design_decisions."
        )
    )
    system_context_diagram_desc: str = Field(
        description="Textual explanation of the system context and external interactions."
    )
    high_level_component_diagram_desc: str = Field(
        description="Narrative explanation of major components and their responsibilities."
    )
    data_flow_desc: str = Field(
        description="Step-by-step explanation of key data flows and lifecycle."
    )
    external_interfaces: List[str] = Field(
        description=(
            "Third-party systems, SaaS platforms, or partner integrations. "
            "Example: Payment Gateway, Identity Provider, Analytics Platform."
        )
    )
    user_stories: List[str] = Field(
        description=(
            "High-level user stories mapping business goals to system behavior. "
            "Example: 'As a customer, I can track my order status in real time'."
        )
    )
    tech_stack: Dict[str, str] = Field(
        description=(
            "Mapping of architectural layers or components to technologies. "
            "Example: {'Frontend': 'React', 'API': 'FastAPI', 'DB': 'PostgreSQL'}. "
            "Non-standard choices must be justified."
        )
    )

class ComponentSpec(BaseModel):
    name: str
    responsibility: str = Field(
        description=(
            "Single, clearly bounded responsibility of the component. "
            "Must adhere to Single Responsibility Principle."
        )
    )
    design_patterns: List[str] = Field(
        description="Design patterns applied (e.g., CQRS, Saga, Factory, Observer)."
    )
    communication_protocols: List[str] = Field(
        description="Protocols used (REST, gRPC, AMQP, Kafka, WebSockets)."
    )
    sync_async_boundaries: str = Field(
        description=(
            "Explanation of synchronous vs asynchronous interactions and trade-offs "
            "(latency, reliability, coupling)."
        )
    )
    trust_boundaries: str = Field(
        description="Security and trust boundaries crossed by this component."
    )
    component_dependencies: List[str] = Field(
        description="Other components or services this component depends on."
    )
    component_metrics: List[str] = Field(
        description=(
            "Key KPIs and SLOs. Example: 'p99 latency < 200ms', '99.99% availability'."
        )
    )
    component_ownership: str = Field(
        description="Owning team or role responsible for lifecycle and on-call."
    )

class DataArchitecture(BaseModel):
    data_ownership_map: Dict[str, str] = Field(
        description="Mapping of service/component to the data it owns."
    )
    storage_choices: Dict[str, str] = Field(
        description="Mapping of service/component to storage technology."
    )
    data_classification: Literal["Public", "Internal", "Confidential", "Restricted"] = Field(
        description="Highest sensitivity level of data handled by the system."
    )
    consistency_model: Literal["Strong", "Eventual", "Causal"] = Field(
        description=(
            "Consistency guarantees provided. Strong consistency must be explicitly justified."
        )
    )
    data_retention_policy: str = Field(
        description="How long data is retained and deletion policies (legal/compliance driven)."
    )
    data_backup_recovery: str = Field(
        description="Backup frequency, storage location, and recovery procedures."
    )
    schema_evolution_strategy: str = Field(
        description=(
            "Approach for backward-compatible schema changes "
            "(e.g., expand-and-contract, versioned schemas)."
        )
    )

class IntegrationStrategy(BaseModel):
    public_apis: List[str] = Field(
        description="Externally exposed APIs and their purpose."
    )
    internal_apis: List[str] = Field(
        description="Internal service-to-service APIs."
    )
    api_gateway_strategy: str = Field(
        description="Role of API Gateway: routing, auth, rate limiting, observability."
    )
    api_documentation: str = Field(
        description="API documentation tooling and standards (OpenAPI, Swagger, GraphQL SDL)."
    )
    contract_strategy: Literal["OpenAPI", "Protobuf", "GraphQL", "Thrift"] = Field(
        description="Primary API contract definition approach."
    )
    versioning_strategy: str = Field(
        description="API and contract versioning approach."
    )
    backward_compatibility_plan: str = Field(
        description="How breaking changes are avoided and deprecations handled."
    )

class NFRs(BaseModel):
    scalability_plan: str = Field(
        description="Horizontal vs vertical scaling strategy and triggers."
    )
    availability_slo: str = Field(
        description="Target availability SLO (e.g., 99.99%)."
    )
    latency_targets: str = Field(
        description="Latency objectives (p50/p95/p99) for critical paths."
    )
    security_requirements: List[str] = Field(
        description="Mandatory security requirements derived from threat modeling."
    )
    reliability_targets: str = Field(
        description="Error budgets, MTTR, and failure tolerance."
    )
    maintainability_plan: str = Field(
        description="Code quality, modularity, documentation, and ownership practices."
    )
    cost_constraints: str = Field(
        description="Budget limits, cost optimization goals, and trade-offs."
    )
    load_testing_strategy: str = Field(
        description="Load and stress testing tools, scenarios, and success criteria."
    )

class SecurityCompliance(BaseModel):
    threat_model_summary: str = Field(
        description="Summary of major threats and mitigations (e.g., STRIDE-based)."
    )
    authentication_strategy: str = Field(
        description="Authentication approach (OAuth2, OIDC, SSO, MFA)."
    )
    authorization_strategy: str = Field(
        description="Authorization model (RBAC, ABAC, policy-based)."
    )
    secrets_management: str = Field(
        description="How secrets are stored, rotated, and accessed."
    )
    data_encryption_at_rest: str = Field(
        description="Encryption standards for stored data."
    )
    data_encryption_in_transit: str = Field(
        description="TLS standards and enforcement."
    )
    auditing_mechanisms: str = Field(
        description="Audit logs, access trails, and retention."
    )
    compliance_certifications: List[str] = Field(
        description="Applicable compliance standards (SOC2, ISO 27001, GDPR, HIPAA)."
    )

class ReliabilityResilience(BaseModel):
    failover_strategy: str = Field(
        description="Failover, redundancy, and load balancing approach."
    )
    disaster_recovery_rpo_rto: str = Field(
        description="RPO/RTO targets and disaster recovery plan."
    )
    self_healing_mechanisms: str = Field(
        description="Auto-scaling, restarts, and remediation triggers."
    )
    retry_backoff_strategy: str = Field(
        description="Retry policies and exponential backoff strategies."
    )
    circuit_breaker_policy: str = Field(
        description="Circuit breaker thresholds and behavior."
    )

class ObservabilityStrategy(BaseModel):
    logging_strategy: str = Field(
        description="Log levels, formats, correlation IDs, and retention."
    )
    metrics_collection: List[str] = Field(
        description="Key system and business metrics collected."
    )
    tracing_strategy: str = Field(
        description="Distributed tracing standards and tooling."
    )
    alerting_rules: List[str] = Field(
        description="Alert thresholds and escalation policies."
    )

class DeploymentOperations(BaseModel):
    cloud_provider: str = Field(
        description="Cloud or hosting provider (AWS, GCP, Azure, Hybrid)."
    )
    deployment_model: Literal["Serverless", "Containers", "VMs", "On-Prem"] = Field(
        description="Primary compute deployment model."
    )
    cicd_pipeline: str = Field(
        description="CI/CD tooling and stages from commit to production."
    )
    deployment_strategy: Literal["Blue-Green", "Canary", "Rolling", "Recreate"] = Field(
        description="Production deployment approach."
    )
    feature_flag_strategy: str = Field(
        description="Feature toggle system and rollout strategy."
    )
    rollback_strategy: str = Field(
        description="Automated and manual rollback procedures."
    )
    operational_monitoring: str = Field(
        description="Dashboards and operational health monitoring."
    )
    git_repository_management: str = Field(
        description="Branching, review, and release management strategy."
    )

class DesignDecisions(BaseModel):
    patterns_used: List[str] = Field(
        description="Key architectural and design patterns applied."
    )
    tech_stack_justification: str = Field(
        description="Rationale for chosen technologies."
    )
    trade_off_analysis: str = Field(
        description=(
            "Explicit discussion of major trade-offs "
            "(e.g., scalability vs consistency, cost vs reliability)."
        )
    )
    rejected_alternatives: List[str] = Field(
        description="Alternatives considered and reasons for rejection."
    )

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
    diagrams: Optional[ArchitectureDiagrams] = Field(
        default=None,
        description="Optional generated diagram code artifacts."
    )
    citations: Optional[List[Citation]] = None

# ==========================================
# 🧠 SECTION 2: LOW-LEVEL DESIGN (LLD)
# ==========================================

class InternalComponentDesign(BaseModel):
    component_name: str = Field(
        description="Name of the component as referenced in HLD. Must match exactly."
    )
    class_structure_desc: str = Field(
        description=(
            "Detailed description of internal class structure, responsibilities, "
            "and relationships. Should explain key classes, interfaces, and patterns "
            "used (e.g., service classes, repositories, adapters)."
        )
    )
    module_boundaries: str = Field(
        description=(
            "Explanation of module/package boundaries and dependency rules. "
            "Clarify what is public vs internal and how cohesion is enforced."
        )
    )
    interface_specifications: List[str] = Field(
        description=(
            "Public interfaces exposed by this component. "
            "May include API endpoints, public methods, or event contracts. "
            "Example: 'POST /orders', 'OrderService.createOrder()'."
        )
    )
    dependency_direction: str = Field(
        description=(
            "Allowed dependency flow (e.g., inward-only, domain → infrastructure). "
            "Must align with architectural principles such as Clean Architecture."
        )
    )
    error_handling_local: str = Field(
        description=(
            "Component-level error handling strategy. "
            "Include error categories, retry behavior, idempotency, and "
            "how errors propagate to callers."
        )
    )
    versioning: str = Field(
        description=(
            "Internal versioning approach for the component. "
            "Example: semantic versioning, backward-compatible changes policy."
        )
    )
    security_considerations: str = Field(
        description=(
            "Security checks performed within the component. "
            "Include input validation, authorization enforcement, "
            "and protection against common vulnerabilities."
        )
    )

class APIEndpointDetail(BaseModel):
    endpoint: str = Field(
        description="Canonical API path (e.g., /api/v1/orders/{id})."
    )
    method: str = Field(
        description="HTTP method (GET, POST, PUT, DELETE, PATCH)."
    )
    request_schema: str = Field(
        description=(
            "Request payload schema. May reference JSON Schema, OpenAPI component, "
            "or Protobuf message."
        )
    )
    response_schema: str = Field(
        description=(
            "Response payload schema for successful responses."
        )
    )
    error_codes: List[str] = Field(
        description=(
            "All possible error codes returned by this endpoint. "
            "Include HTTP status mapping and business error codes."
        )
    )
    rate_limiting_rule: str = Field(
        description=(
            "Rate limiting policy applied. "
            "Example: '100 requests/min per user, burst 20'."
        )
    )
    authorization_mechanism: str = Field(
        description=(
            "Authorization required to access this endpoint. "
            "Example: 'JWT with ROLE_ADMIN', 'OAuth2 scope: orders:write'."
        )
    )
    api_gateway_integration: str = Field(
        description=(
            "How this endpoint is exposed through the API Gateway. "
            "Include routing, auth enforcement, throttling, and logging."
        )
    )
    testing_strategy: str = Field(
        description=(
            "Testing approach specific to this endpoint. "
            "Include functional, security, negative, and load test coverage."
        )
    )
    versioning_strategy: str = Field(
        description=(
            "Endpoint versioning approach (URL versioning, headers, or media types)."
        )
    )

class DataModelDetail(BaseModel):
    entity: str = Field(
        description="Name of the domain entity or table."
    )
    attributes: List[str] = Field(
        description="List of attributes/columns with types and purpose."
    )
    indexes: List[str] = Field(
        description="Indexes defined to support query patterns and performance."
    )
    constraints: List[str] = Field(
        description="Database constraints (unique, not-null, check, etc.)."
    )
    validation_rules: List[str] = Field(
        description=(
            "Domain-level validation rules beyond DB constraints. "
            "Example: 'order_total must be > 0'."
        )
    )
    foreign_keys: List[str] = Field(
        description="Foreign key relationships and cardinality."
    )
    migration_strategy: str = Field(
        description=(
            "Approach for evolving this data model. "
            "Include backward compatibility and rollback considerations."
        )
    )

class BusinessLogic(BaseModel):
    core_algorithms: str = Field(
        description=(
            "Description or pseudocode of critical business algorithms. "
            "Focus on non-trivial logic that impacts correctness or performance."
        )
    )
    state_machine_desc: Optional[str] = Field(
        description=(
            "State machine description if applicable. "
            "Include states, transitions, and invalid transitions."
        )
    )
    concurrency_control: str = Field(
        description=(
            "Concurrency handling strategy (optimistic locking, pessimistic locking, "
            "idempotency keys, distributed locks)."
        )
    )
    async_processing_details: Optional[str] = Field(
        description=(
            "Asynchronous workflows, background jobs, or event handling logic."
        )
    )

class ErrorHandlingStrategy(BaseModel):
    error_taxonomy: str = Field(
        description=(
            "Classification of errors (validation, business, system, external dependency)."
        )
    )
    custom_error_codes: List[str] = Field(
        description="Standardized internal error codes and meanings."
    )
    retry_policies: str = Field(
        description=(
            "Retry behavior for transient failures. "
            "Include limits, backoff, and idempotency guarantees."
        )
    )
    dlq_strategy: Optional[str] = Field(
        description=(
            "Dead-letter queue usage for failed async processing, if applicable."
        )
    )
    exception_handling_framework: str = Field(
        description=(
            "Frameworks or patterns used for exception handling "
            "(e.g., global exception mappers, middleware)."
        )
    )

class SecurityImplementation(BaseModel):
    input_validation_rules: str = Field(
        description=(
            "Validation rules enforced at boundaries to prevent malformed or malicious input."
        )
    )
    auth_flow_diagram_desc: str = Field(
        description="Textual description of authentication and authorization flow."
    )
    token_management: str = Field(
        description=(
            "Token lifecycle management including expiry, refresh, revocation, and rotation."
        )
    )
    encryption_details: str = Field(
        description=(
            "Specific cryptographic algorithms and key management practices "
            "(e.g., AES-256, RSA-2048, KMS integration)."
        )
    )

class PerformanceEng(BaseModel):
    caching_strategy: str = Field(
        description=(
            "Caching layers and policies (in-memory, distributed, HTTP caching)."
        )
    )
    cache_invalidation: str = Field(
        description=(
            "Cache invalidation strategy and consistency guarantees."
        )
    )
    async_processing_desc: str = Field(
        description=(
            "Use of async processing to improve throughput and latency."
        )
    )
    load_balancing_strategy: str = Field(
        description=(
            "Traffic distribution strategy across instances or services."
        )
    )

class TestingStrategy(BaseModel):
    unit_test_scope: str = Field(
        description=(
            "What is covered by unit tests and expected isolation level."
        )
    )
    integration_test_scope: str = Field(
        description=(
            "Cross-component and external dependency testing scope."
        )
    )
    contract_testing_tools: str = Field(
        description=(
            "Tools and approach for consumer-driven or provider contract testing."
        )
    )
    chaos_engineering_plan: Optional[str] = Field(
        description=(
            "Fault injection and resilience testing plan, if applicable."
        )
    )
    test_coverage_metrics: str = Field(
        description=(
            "Coverage targets and quality gates (line, branch, mutation coverage)."
        )
    )

class OperationalReadiness(BaseModel):
    runbook_summary: str = Field(
        description="Operational runbook overview for on-call engineers."
    )
    incident_response_plan: str = Field(
        description="Incident detection, escalation, and communication process."
    )
    monitoring_and_alerts: List[str] = Field(
        description="Key alerts, dashboards, and SLO-based monitoring signals."
    )
    backup_recovery_procedures: str = Field(
        description="Operational procedures for backup verification and recovery."
    )

class DocumentationGovernance(BaseModel):
    code_docs_standard: str = Field(
        description="Code documentation standards (docstrings, comments, style guides)."
    )
    api_docs_tooling: str = Field(
        description="API documentation tooling and publishing process."
    )
    adr_process: str = Field(
        description="Architecture Decision Record (ADR) creation and approval process."
    )
    document_review_process: str = Field(
        description="Review cadence, approvers, and update triggers."
    )
    internal_vs_public_docs: str = Field(
        description="Rules governing what documentation is internal vs externally visible."
    )

class LowLevelDesign(BaseModel):
    """Items 12–22 of the Framework"""
    detailed_components: List[InternalComponentDesign]
    api_design: List[APIEndpointDetail]
    data_model_deep_dive: List[DataModelDetail]
    business_logic: BusinessLogic
    consistency_concurrency: str = Field(
        description="System-wide consistency and concurrency guarantees."
    )
    error_handling: ErrorHandlingStrategy
    security_implementation: SecurityImplementation
    performance_engineering: PerformanceEng
    testing_strategy: TestingStrategy
    operational_readiness: OperationalReadiness
    documentation_governance: DocumentationGovernance
    citations: Optional[List[Citation]] = None

# ==========================================
# 🛠️ SECTION 3: ARTIFACTS & METRICS
# ==========================================

class JudgeVerdict(BaseModel):
    is_valid: bool = False
    critique: str = "Summary of issues found in HLD and LLD."
    score: int = 0  # 0-100 overall quality score
    
    # New structured issue categories
    hld_lld_mismatch: Optional[List[str]] = None
    security_gaps: Optional[List[str]] = None
    nfr_mismatches: Optional[List[str]] = None
    diagram_issues: Optional[List[str]] = None
    testing_coverage_gaps: Optional[List[str]] = None
    
    # Recommended actions for iteration
    iteration_recommendations: Optional[List[str]] = None

class DiagramCode(BaseModel):
    python_code: str = Field(
        description="Executable Python code using the 'diagrams' library."
    )

class FileSpec(BaseModel):
    filename: str = Field(
        description="Relative file path."
    )
    content: str = Field(
        description="File contents."
    )
    language: str = Field(
        default="python",
        description="Programming or markup language."
    )

class ScaffoldingSpec(BaseModel):
    folder_structure: str = Field(
        description="ASCII tree representation of the project structure."
    )
    starter_files: List[FileSpec] = Field(
        description="Initial set of generated files."
    )
    cookiecutter_url: Optional[str] = Field(
        description="Optional cookiecutter template reference."
    )

class RunMetrics(BaseModel):
    security_score: float = Field(
        description="Computed security posture score."
    )
    security_reason: str = Field(
        description="Explanation for the security score."
    )
    red_team_issues: List[str] = Field(
        description="Issues identified through adversarial or red-team analysis."
    )
    total_tokens: int = Field(
        default=0,
        description="Total tokens consumed during generation or evaluation."
    )

class RefinedDesign(BaseModel):
    """Container for the output of the Reiteration Agent."""
    hld: HighLevelDesign
    lld: LowLevelDesign
    improvement_notes: str = Field(description="Summary of changes made.")

class DiagramValidationResult(BaseModel):
    """Container for Diagram Validation."""
    valid_syntax: bool
    missing_elements: List[str] = Field(description="Components in HLD but missing in Diagram.")
    invalid_elements: List[str] = Field(description="Elements in Diagram not found in HLD.")
    critique: str