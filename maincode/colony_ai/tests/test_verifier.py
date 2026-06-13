"""
Unit tests for the Colony Verifier.
"""

import unittest
import sys
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from colony.verifier import Verifier
from colony.schemas import SuboperatorResponse

class TestVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = Verifier(confidence_threshold=0.5)

    def test_successful_verification(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.9,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}]
        )
        self.assertTrue(self.verifier.verify(resp))

    def test_rejected_unsuccessful(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=False,
            confidence=0.9,
            facts=[]
        )
        self.assertFalse(self.verifier.verify(resp))

    def test_rejected_errors(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.9,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}],
            errors=["Warning: precision warning"]
        )
        self.assertFalse(self.verifier.verify(resp))

    def test_rejected_low_confidence(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.49,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}]
        )
        self.assertFalse(self.verifier.verify(resp))

    def test_custom_threshold(self):
        strict_verifier = Verifier(confidence_threshold=0.95)
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.90,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}]
        )
        # Should fail strict verification
        self.assertFalse(strict_verifier.verify(resp))
        # Should pass default 0.5 threshold verification
        self.assertTrue(self.verifier.verify(resp))

    def test_schema_validation(self):
        # Missing type
        resp_bad_type = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.9,
            facts=[{"expression": "5 + 5", "result": 10}]
        )
        self.assertFalse(self.verifier.verify(resp_bad_type))

        # Bad math structure
        resp_bad_math = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.9,
            facts=[{"type": "calculation", "result": "not_a_number"}]
        )
        self.assertFalse(self.verifier.verify(resp_bad_math))

    def test_empty_facts_rejection(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.9,
            facts=[]
        )
        self.assertFalse(self.verifier.verify(resp))

    def test_math_recomputation_success_and_failure(self):
        # Correct calculation: 45 * 123 = 5535
        resp_correct = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.99,
            facts=[{"type": "calculation", "expression": "45 * 123", "result": 5535}]
        )
        self.assertTrue(self.verifier.verify(resp_correct))

        # Incorrect calculation: 45 * 123 = 9999 (Success criteria test case!)
        resp_incorrect = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=0.99,
            facts=[{"type": "calculation", "expression": "45 * 123", "result": 9999}]
        )
        self.assertFalse(self.verifier.verify(resp_incorrect))

    def test_verify_all_warnings(self):
        resp = SuboperatorResponse(
            operator="keyword_op",
            success=True,
            confidence=0.80,  # inside [0.70, 0.89]
            facts=[{"type": "greeting", "value": "hello"}]
        )
        result = self.verifier.verify_all([resp])
        self.assertTrue(result.verified)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("usable with warning", result.warnings[0])

    def test_contradiction_resolution(self):
        # operator_a says language is python, confidence is 0.95
        resp_a = SuboperatorResponse(
            operator="operator_a",
            success=True,
            confidence=0.95,
            facts=[{"type": "language", "value": "Python"}]
        )
        # operator_b says language is javascript, confidence is 0.80
        resp_b = SuboperatorResponse(
            operator="operator_b",
            success=True,
            confidence=0.80,
            facts=[{"type": "code_language", "language": "JavaScript"}]
        )

        result = self.verifier.verify_all([resp_a, resp_b])
        # Should keep Python (confidence 0.95) and reject JavaScript (confidence 0.80)
        self.assertTrue(result.verified)
        self.assertEqual(len(result.facts), 1)
        self.assertEqual(result.facts[0]["type"], "language")
        self.assertEqual(result.facts[0]["value"], "Python")
        
        # JavaScript should be in rejected
        self.assertEqual(len(result.rejected), 1)
        self.assertIn("Contradiction", result.rejected[0]["reason"])
        self.assertIn("JavaScript", result.rejected[0]["reason"])

        # Contradiction resolution should be logged in warnings
        self.assertTrue(any("Contradiction resolved" in w for w in result.warnings))

    def test_missing_information(self):
        # Routed math_op but no calculation fact returned
        resp = SuboperatorResponse(
            operator="keyword_op",
            success=True,
            confidence=0.9,
            facts=[{"type": "greeting", "value": "hello"}]
        )
        result = self.verifier.verify_all([resp], query="calculate 45 * 123", routed_operators=["math_op"])
        self.assertIn("No verified facts from routed operator 'math_op'.", result.missing)
        self.assertIn("calculation results (math_op)", result.missing)

if __name__ == "__main__":
    unittest.main()

