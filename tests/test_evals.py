import pytest
import os
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric
from dotenv import load_dotenv
from graph import app_graph

load_dotenv()

# Define a robust scenario
SCENARIO = "Design a ride-sharing backend for 100k users. Must use SQL."

def test_architectural_consistency():
    print(f"\n🧪 Testing Scenario: {SCENARIO}")
    
    # 1. Run the live pipeline
    result = app_graph.invoke({"user_request": SCENARIO, "retry_count": 0})
    hld_txt = result['hld'].model_dump_json()
    lld_txt = result['lld'].model_dump_json()

    # 2. Check Structural Constraints (Zero Cost)
    assert len(result['hld'].components) >= 2, "HLD too simple"
    assert "SQL" in hld_txt or "Postgres" in hld_txt, "Ignored SQL constraint"

    # 3. Check Semantic Relevance (LLM Judge)
    # Did the Manager actually address the user's prompt?
    relevancy = AnswerRelevancyMetric(threshold=0.7)
    
    test_case = LLMTestCase(
        input=SCENARIO,
        actual_output=hld_txt,
        retrieval_context=[lld_txt] 
    )

    assert_test(test_case, [relevancy])