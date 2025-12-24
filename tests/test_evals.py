import pytest
import os
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, GEval
from deepeval.params import GEvalParams
from dotenv import load_dotenv

# We do NOT import app_graph here to avoid triggering live LLM calls during test collection
# from graph import app_graph 

load_dotenv()

# Define a robust scenario
SCENARIO = "Design a ride-sharing backend for 100k users. Must use SQL."

# Mock Data (Replace with real captures for regression testing)
MOCK_HLD = """
{
    "business_context": {"problem_statement": "Ride sharing app..."},
    "architecture_overview": {"tech_stack": [{"layer": "DB", "technology": "PostgreSQL"}]},
    "core_components": [{"name": "RideMatchingService"}, {"name": "UserProfiles"}]
}
"""

MOCK_LLD = """
{
    "detailed_components": [
        {"component_name": "RideMatchingService", "class_structure_desc": "Uses GeoHash..."},
        {"component_name": "UserProfiles", "class_structure_desc": "CRUD operations..."}
    ]
}
"""

def test_answer_relevancy():
    """Checks if the HLD actually addresses the user's prompt."""
    relevancy_metric = AnswerRelevancyMetric(threshold=0.7)
    
    # Retrieval context should be the knowledge base, NOT the LLD.
    # If no KB used, leave empty.
    test_case = LLMTestCase(
        input=SCENARIO,
        actual_output=MOCK_HLD,
        retrieval_context=[] 
    )
    
    assert_test(test_case, [relevancy_metric])

def test_consistency_hld_lld():
    """Checks if LLD implements HLD components using GEval."""
    
    consistency_metric = GEval(
        name="Consistency",
        criteria="Determine if the LLD detailed components match the HLD core components.",
        evaluation_params=[GEvalParams.INPUT, GEvalParams.ACTUAL_OUTPUT],
        threshold=0.6
    )
    
    test_case = LLMTestCase(
        input=MOCK_HLD,  # Treat HLD as the 'requirement'
        actual_output=MOCK_LLD # Treat LLD as the 'implementation'
    )
    
    assert_test(test_case, [consistency_metric])

def test_constraints_adherence():
    """Simple assertion test for constraints."""
    import json
    hld_json = json.loads(MOCK_HLD)
    
    tech_stack = [t['technology'] for t in hld_json['architecture_overview']['tech_stack']]
    
    # Check for SQL requirement
    has_sql = any("SQL" in t or "Postgres" in t or "MySQL" in t for t in tech_stack)
    assert has_sql, "HLD failed to include SQL database as requested."