import unittest
import os
from colony_ai.colony.atma import Atma
from colony_ai.colony.config import DEFAULT_OLLAMA_MODEL, OLLAMA_NUM_THREADS



class TestOptimization(unittest.TestCase):
    def setUp(self):
        self.atma = Atma()

    def test_default_configurations(self):
        # Verify DEFAULT_OLLAMA_MODEL is set to empty string under test environment
        self.assertEqual(DEFAULT_OLLAMA_MODEL, "")
        # Verify default thread optimization limit is 2
        self.assertEqual(OLLAMA_NUM_THREADS, 2)


    def test_fact_compression_calculation(self):
        facts = [
            {"type": "calculation", "expression": "18 / 100 * 25000", "result": 4500.0, "operator": "math_op"}
        ]
        compressed = self.atma._compress_facts(facts)
        self.assertIn("[calc: 18 / 100 * 25000 = 4500.0]", compressed)
        self.assertIn("(math_op)", compressed)

    def test_fact_compression_code_and_syntax(self):
        facts = [
            {"type": "code_language", "language": "python", "operator": "code_op"},
            {"type": "syntax_check", "language": "python", "valid": True, "operator": "code_op"}
        ]
        compressed = self.atma._compress_facts(facts)
        self.assertIn("[code_lang: python]", compressed)
        self.assertIn("[syntax: python is valid]", compressed)

    def test_fact_compression_plan(self):
        facts = [
            {"type": "plan", "steps": ["step 1", "step 2"], "operator": "planner_op"}
        ]
        compressed = self.atma._compress_facts(facts)
        self.assertIn("[plan: step 1, step 2]", compressed)

    def test_fact_compression_tool_call(self):
        facts = [
            {
                "type": "tool_call",
                "tool": "calculator",
                "input": "45 * 123",
                "success": True,
                "output": 5535,
                "operator": "math_op"
            }
        ]
        compressed = self.atma._compress_facts(facts)
        self.assertIn("[tool: calculator(45 * 123) -> success: 5535]", compressed)

    def test_fact_compression_memory(self):
        facts = [
            {"type": "stored_preference", "key": "color", "value": "red", "operator": "memory_op"},
            {"type": "preference_not_found", "key": "age", "operator": "memory_op"}
        ]
        compressed = self.atma._compress_facts(facts)
        self.assertIn("[memory: color = red]", compressed)
        self.assertIn("[memory: age not found]", compressed)

if __name__ == "__main__":
    unittest.main()
