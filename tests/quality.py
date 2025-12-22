from deepeval.metrics import GEval, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

# Custom Security Metric using LLM-as-a-Judge
security_metric = GEval(
    name="Security Hardening",
    criteria="""
    The system design MUST:
    1. Explicitly mention authentication (OAuth, JWT, etc).
    2. Encrypt data at rest and in transit.
    3. Follow least-privilege principles.
    Fail if it allows public access to private data or mentions plaintext passwords.
    """,
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.7
)

def evaluate_design(user_request, hld_json):
    """Runs DeepEval security metric."""
    test_case = LLMTestCase(
        input=user_request,
        actual_output=hld_json
    )
    
    try:
        security_score = security_metric.measure(test_case)
        reason = security_metric.reason
    except Exception as e:
        print(f"Eval Error: {e}")
        security_score = 0.5
        reason = "Evaluation failed due to LLM error."

    return {
        "security_score": security_score,
        "security_reason": reason,
        "is_safe": security_score > 0.7
    }

def red_team_probe(hld_json):
    """Simulates a Red Team scan for obvious vulnerabilities."""
    vulnerabilities = []
    hld_lower = hld_json.lower()
    
    if "allow all" in hld_lower or "0.0.0.0/0" in hld_lower:
        vulnerabilities.append("Overly permissive firewall rules detected.")
    if "plaintext" in hld_lower or "no auth" in hld_lower:
        vulnerabilities.append("Plaintext storage or missing auth detected.")
    if "admin" in hld_lower and "password" in hld_lower and "hardcoded" in hld_lower:
        vulnerabilities.append("Hardcoded admin credentials suspected.")
        
    return vulnerabilities