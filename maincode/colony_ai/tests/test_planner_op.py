"""
Unit tests for the PlannerOperator.
"""

import unittest
import sys
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from suboperators.planner_op import PlannerOperator

class TestPlannerOp(unittest.TestCase):
    def setUp(self):
        self.operator = PlannerOperator()

    def test_name(self):
        self.assertEqual(self.operator.name, "planner_op")

    def test_no_plan_steps_error(self):
        res = self.operator.execute("")
        self.assertFalse(res.success)
        self.assertEqual(res.confidence, 0.0)
        self.assertTrue(len(res.errors) > 0)

    def test_simple_sequential_plan(self):
        # Plan building a house then painting it.
        res = self.operator.execute("Plan building a house then painting it.")
        self.assertTrue(res.success)
        
        plan_fact = next(f for f in res.facts if f["type"] == "plan")
        self.assertEqual(len(plan_fact["steps"]), 2)
        self.assertEqual(plan_fact["steps"][0], "Building a house")
        self.assertEqual(plan_fact["steps"][1], "Painting it")
        
        # Check dependencies
        self.assertIn("Painting it", plan_fact["dependencies"])
        self.assertEqual(plan_fact["dependencies"]["Painting it"], ["Building a house"])

    def test_conjunction_and_splitting(self):
        # Split using "and" with verb triggers
        res = self.operator.execute("Calculate 18% GST on 25000 and write a short explanation.")
        self.assertTrue(res.success)
        
        plan_fact = next(f for f in res.facts if f["type"] == "plan")
        self.assertEqual(len(plan_fact["steps"]), 2)
        self.assertEqual(plan_fact["steps"][0], "Calculate 18% GST on 25000")
        self.assertEqual(plan_fact["steps"][1], "Write a short explanation")

    def test_complex_multi_step_plan(self):
        # Semicolon and transition word splits
        res = self.operator.execute("Build router; add math_op; and then add verifier")
        self.assertTrue(res.success)
        
        plan_fact = next(f for f in res.facts if f["type"] == "plan")
        self.assertEqual(len(plan_fact["steps"]), 3)
        self.assertEqual(plan_fact["steps"][0], "Build router")
        self.assertEqual(plan_fact["steps"][1], "Add math_op")
        self.assertEqual(plan_fact["steps"][2], "Add verifier")

        self.assertEqual(plan_fact["dependencies"]["Add math_op"], ["Build router"])
        self.assertEqual(plan_fact["dependencies"]["Add verifier"], ["Add math_op"])

if __name__ == "__main__":
    unittest.main()
