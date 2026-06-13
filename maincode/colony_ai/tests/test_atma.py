"""
Unit tests for the Colony Atma Voice Synthesizer templates.
"""

import unittest
import unittest.mock
import subprocess
import sys
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from colony.atma import Atma
from colony.schemas import SuboperatorResponse, VerificationResult

class TestAtma(unittest.TestCase):
    def setUp(self):
        self.atma = Atma()

    def test_math_no_explain(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "45 * 123", "result": 5535}]
        )
        output = self.atma.speak("calculate 45 * 123", [resp])
        self.assertEqual(output.strip(), "45 * 123 = 5535.")

    def test_math_explain_multiplication(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "45 * 123", "result": 5535}]
        )
        output = self.atma.speak("calculate 45 * 123 and explain it", [resp])
        self.assertEqual(output.strip(), "45 * 123 = 5535. This means 45 multiplied by 123 gives 5535.")

    def test_math_explain_addition(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "100 + 250", "result": 350}]
        )
        output = self.atma.speak("explain this addition 100 + 250", [resp])
        self.assertEqual(output.strip(), "100 + 250 = 350. This means 100 added to 250 gives 350.")

    def test_percentage_explain(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "(18 / 100) * 25000", "result": 4500.0}]
        )
        output = self.atma.speak("calculate 18% on 25000 and explain", [resp])
        self.assertEqual(output.strip(), "(18 / 100) * 25000 = 4500.0. This means 18% of 25000 gives 4500.")

    def test_missing_facts_fallback(self):
        # Empty responses
        output = self.atma.speak("do something", [])
        expected = "I could not find enough verified information to answer safely. I detected the topic, but no reliable calculation or fact was produced."
        self.assertEqual(output.strip(), expected)

    def test_keyword_formatting(self):
        resp = SuboperatorResponse(
            operator="keyword_op",
            success=True,
            confidence=1.0,
            facts=[
                {"type": "greeting", "value": "Welcome to the Colony"},
                {"type": "keyword_match", "keyword": "colony", "value": "An AI framework"}
            ]
        )
        output = self.atma.speak("hello colony", [resp])
        self.assertIn("Welcome to the Colony", output)
        self.assertIn("Matched keyword 'colony': An AI framework", output)

    def test_code_op_formatting(self):
        resp = SuboperatorResponse(
            operator="code_op",
            success=True,
            confidence=0.9,
            facts=[
                {"type": "code_language", "language": "python", "confidence": 0.95},
                {"type": "syntax_check", "valid": False, "error": "invalid syntax", "line": 5, "offset": 4},
                {"type": "bug_category", "category": "indentation", "description": "spaces mismatch", "line": 5}
            ]
        )
        output = self.atma.speak("check python code", [resp])
        self.assertIn("Detected programming language: python (confidence: 0.95).", output)
        self.assertIn("Syntax check: Code has syntax errors: invalid syntax at line 5, offset 4.", output)
        self.assertIn("Bug analysis: Identified indentation issue: spaces mismatch (line 5).", output)

    def test_planner_op_formatting(self):
        resp = SuboperatorResponse(
            operator="planner_op",
            success=True,
            confidence=0.9,
            facts=[{
                "type": "plan",
                "steps": ["Step A", "Step B"],
                "dependencies": {"Step B": ["Step A"]}
            }]
        )
        output = self.atma.speak("plan steps", [resp])
        self.assertIn("Decomposed Plan:", output)
        self.assertIn("1. Step A", output)
        self.assertIn("2. Step B (depends on: Step A)", output)

    def test_debug_mode(self):
        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "10 * 10", "result": 100}]
        )
        verification_result = VerificationResult(
            verified=True,
            facts=[{"type": "calculation", "expression": "10 * 10", "result": 100, "operator": "math_op"}],
            rejected=[],
            warnings=[],
            missing=[]
        )
        output = self.atma.speak(
            query="calculate 10 * 10",
            verified_responses=[resp],
            verbose=True,
            verification_result=verification_result,
            routed_operators=["math_op"]
        )
        self.assertIn("10 * 10 = 100.", output)
        self.assertIn("--- Debug Output ---", output)
        self.assertIn("Selected operators: math_op", output)
        self.assertIn("Verified facts: 1", output)
        self.assertIn("Rejected facts: 0", output)
        self.assertIn("Final answer: 10 * 10 = 100.", output)

    @unittest.mock.patch("subprocess.run")
    def test_speak_model_success(self, mock_run):
        # Configure subprocess mock to return a successful run
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "This is the model generated response."
        mock_run.return_value = mock_result

        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}]
        )
        
        # Test model invocation
        output = self.atma.speak(
            query="calculate 5 + 5",
            verified_responses=[resp],
            model_name="dummy:model",
            ollama_path="dummy-ollama"
        )
        
        self.assertEqual(output.strip(), "This is the model generated response.")
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["dummy-ollama", "run", "dummy:model"])
        self.assertIn("USER_PROMPT:\ncalculate 5 + 5", kwargs["input"])

    @unittest.mock.patch("subprocess.run")
    def test_speak_model_fallback_on_failure(self, mock_run):
        # Configure subprocess mock to simulate failure (exit code 1)
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Model error details"
        mock_run.return_value = mock_result

        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}]
        )
        
        # Test fallback: it should return template response "5 + 5 = 10." instead of failing
        output = self.atma.speak(
            query="calculate 5 + 5",
            verified_responses=[resp],
            model_name="dummy:model",
            ollama_path="dummy-ollama"
        )
        
        self.assertEqual(output.strip(), "5 + 5 = 10.")
        mock_run.assert_called_once()

    @unittest.mock.patch("subprocess.run")
    def test_speak_model_fallback_on_timeout(self, mock_run):
        # Configure subprocess mock to throw timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["ollama"], timeout=45)

        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}]
        )
        
        output = self.atma.speak(
            query="calculate 5 + 5",
            verified_responses=[resp],
            model_name="dummy:model",
            ollama_path="dummy-ollama"
        )
        
        self.assertEqual(output.strip(), "5 + 5 = 10.")
        mock_run.assert_called_once()

    @unittest.mock.patch("urllib.request.urlopen")
    def test_speak_http_api_success(self, mock_urlopen):
        # Configure urlopen mock to return 200 with JSON payload
        mock_response = unittest.mock.Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"response": "HTTP API response text"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}]
        )

        output = self.atma.speak(
            query="calculate 5 + 5",
            verified_responses=[resp],
            model_name="dummy:model",
            ollama_api_url="http://dummy-api"
        )

        self.assertEqual(output.strip(), "HTTP API response text")
        mock_urlopen.assert_called_once()

    @unittest.mock.patch("subprocess.run")
    @unittest.mock.patch("urllib.request.urlopen")
    def test_speak_http_api_fallback_to_cli(self, mock_urlopen, mock_run):
        # Configure urlopen to raise an exception (HTTP API down)
        mock_urlopen.side_effect = Exception("Connection refused")

        # Configure subprocess mock to return a successful run
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Subprocess CLI response"
        mock_run.return_value = mock_result

        resp = SuboperatorResponse(
            operator="math_op",
            success=True,
            confidence=1.0,
            facts=[{"type": "calculation", "expression": "5 + 5", "result": 10}]
        )

        output = self.atma.speak(
            query="calculate 5 + 5",
            verified_responses=[resp],
            model_name="dummy:model",
            ollama_path="dummy-ollama",
            ollama_api_url="http://dummy-api"
        )

        self.assertEqual(output.strip(), "Subprocess CLI response")
        mock_urlopen.assert_called_once()
        mock_run.assert_called_once()

if __name__ == "__main__":
    unittest.main()

