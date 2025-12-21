from pydantic import BaseModel, Field
from typing import List, Optional

# --- High Level Design (Manager) ---
class Component(BaseModel):
    name: str = Field(description="Name of the service (e.g., 'Payment Service')")
    tech_stack: str = Field(description="Language/Framework choice")
    purpose: str = Field(description="Responsibility of this component")

class ArchitecturalDecision(BaseModel):
    title: str
    decision: str
    reasoning: str = Field(description="Trade-off analysis (e.g. why SQL vs NoSQL)")

class HighLevelDesign(BaseModel):
    system_overview: str
    components: List[Component]
    decisions: List[ArchitecturalDecision]

# --- Low Level Design (Team Lead) ---
class DBTable(BaseModel):
    table_name: str
    columns: List[str] = Field(description="e.g. ['id SERIAL PK', 'user_id INT']")

class APIEndpoint(BaseModel):
    method: str = Field(description="GET, POST, PUT, DELETE")
    path: str = Field(description="/api/v1/resource")
    description: str

class LowLevelDesign(BaseModel):
    database_schema: List[DBTable]
    api_specs: List[APIEndpoint]

# --- Quality Control (Judge) ---
class JudgeVerdict(BaseModel):
    is_valid: bool = Field(description="True if LLD matches HLD and requirements")
    critique: str = Field(description="Specific instructions on what to fix if invalid")
    score: int = Field(description="Quality score 1-10")