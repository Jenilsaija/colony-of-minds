"""
Unit tests for the Colony Router.
"""

import unittest
import sys
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from colony.router import Router
from colony.schemas import RouterResponse

class TestRouter(unittest.TestCase):
    def setUp(self):
        self.router = Router()

    def test_fallback_routing(self):
        # Query that triggers fallback
        res = self.router.route("something random that does not trigger anything")
        self.assertEqual(res.selected_operators, ["keyword_op"])
        self.assertEqual(res.confidence, 0.5)
        self.assertIn("falling back", res.reason.lower())

    def test_keyword_greeting_routing(self):
        # Query containing greetings or framework keywords
        res = self.router.route("hello there")
        self.assertEqual(res.selected_operators, ["keyword_op"])
        self.assertEqual(res.confidence, 0.9)  # keyword-only match
        self.assertIn("keyword(s)", res.reason.lower())

    def test_math_routing(self):
        # Math operator activated via keyword calculate
        res1 = self.router.route("calculate 45 * 123")
        self.assertEqual(res1.selected_operators, ["math_op"])
        self.assertEqual(res1.confidence, 0.95) # keyword + pattern trigger
        
        # Math operator activated via arithmetic regex pattern only
        res2 = self.router.route("100 / 4")
        self.assertEqual(res2.selected_operators, ["math_op"])
        self.assertEqual(res2.confidence, 0.85) # pattern only

    def test_code_routing(self):
        # Code operator activated via keyword python
        res1 = self.router.route("fix this python code syntax")
        self.assertEqual(res1.selected_operators, ["code_op"])
        self.assertEqual(res1.confidence, 0.90) # keyword match
        
        # Code operator activated via code definition pattern
        res2 = self.router.route("def print_result(val):")
        self.assertEqual(res2.selected_operators, ["code_op"])
        self.assertEqual(res2.confidence, 0.85) # pattern only

    def test_planner_routing(self):
        # Planner operator activated via keyword plan
        res = self.router.route("write down a plan for the project steps")
        self.assertEqual(res.selected_operators, ["planner_op"])
        self.assertEqual(res.confidence, 0.90)

    def test_multi_label_routing(self):
        # Prompt requiring both math calculation and explanatory keyword routing
        res = self.router.route("Calculate 45 * 123 and explain it.")
        self.assertEqual(res.selected_operators, ["keyword_op", "math_op"])
        self.assertEqual(res.confidence, 0.95)  # math has keyword + pattern, keyword_op has keyword
        self.assertIn("math_op", res.selected_operators)
        self.assertIn("keyword_op", res.selected_operators)

if __name__ == "__main__":
    unittest.main()
