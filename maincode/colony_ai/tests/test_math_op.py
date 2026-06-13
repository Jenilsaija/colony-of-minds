"""
Unit tests for the SafeCalculator and MathOperator.
"""

import unittest
import sys
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from suboperators.math_op import SafeCalculator, MathOperator

class TestMathOp(unittest.TestCase):
    def setUp(self):
        self.calc = SafeCalculator()
        self.operator = MathOperator()

    def test_basic_arithmetic(self):
        self.assertEqual(self.calc.evaluate("5 + 3"), 8)
        self.assertEqual(self.calc.evaluate("10 - 4"), 6)
        self.assertEqual(self.calc.evaluate("3 * 4"), 12)
        self.assertEqual(self.calc.evaluate("10 / 2"), 5.0)

    def test_complex_precedence(self):
        self.assertEqual(self.calc.evaluate("2 + 3 * 4"), 14)
        self.assertEqual(self.calc.evaluate("(2 + 3) * 4"), 20)
        self.assertEqual(self.calc.evaluate("-5 + 10"), 5)

    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            self.calc.evaluate("10 / 0")
        with self.assertRaises(ZeroDivisionError):
            self.calc.evaluate("5 // 0")
        with self.assertRaises(ZeroDivisionError):
            self.calc.evaluate("4 % 0")

    def test_exponentiation_safety_bounds(self):
        # Allow reasonable sizes
        self.assertEqual(self.calc.evaluate("2 ** 8"), 256)
        
        # Block excessive bounds to prevent DOS
        with self.assertRaises(ValueError):
            self.calc.evaluate("2 ** 101")
        with self.assertRaises(ValueError):
            self.calc.evaluate("10001 ** 2")

    def test_syntax_or_type_errors(self):
        with self.assertRaises(ValueError):
            self.calc.evaluate("import os; os.system('echo hi')")  # execution attempt blocked
        with self.assertRaises(ValueError):
            self.calc.evaluate("x = 5")  # assignment blocked
        with self.assertRaises(TypeError):
            self.calc.evaluate("5 + 'hello'")  # type mismatch / unsupported node
        with self.assertRaises(ValueError):
            self.calc.evaluate("5 + ")  # syntax parsing error

    def test_math_operator_execute(self):
        # Test full operator wrapping
        res = self.operator.execute("calculate 45 * 123")
        self.assertTrue(res.success)
        self.assertEqual(res.operator, "math_op")
        self.assertEqual(res.confidence, 1.0)
        self.assertEqual(res.facts[0]["result"], 5535)

        # Test failure case
        res_fail = self.operator.execute("calculate 10 / 0")
        self.assertFalse(res_fail.success)
        self.assertEqual(res_fail.confidence, 0.0)
        self.assertTrue(len(res_fail.errors) > 0)
        self.assertIn("Division or modulo by zero", res_fail.errors[0])

    def test_percentage_calculations(self):
        # Test 18% GST on 25000
        res = self.operator.execute("Calculate 18% GST on 25000")
        self.assertTrue(res.success)
        self.assertEqual(res.facts[0]["result"], 4500.0)

        # Test X% of Y pattern
        res2 = self.operator.execute("what is 15% of 200?")
        self.assertTrue(res2.success)
        self.assertEqual(res2.facts[0]["result"], 30.0)

if __name__ == "__main__":
    unittest.main()
