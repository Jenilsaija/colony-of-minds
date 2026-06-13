"""
Unit tests for the CodeOperator.
"""

import unittest
import sys
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from suboperators.code_op import CodeOperator

class TestCodeOp(unittest.TestCase):
    def setUp(self):
        self.operator = CodeOperator()

    def test_name(self):
        self.assertEqual(self.operator.name, "code_op")

    def test_no_code_error(self):
        res = self.operator.execute("Just a plain English conversational query with no code structure.")
        self.assertFalse(res.success)
        self.assertEqual(res.confidence, 0.0)
        self.assertTrue(len(res.errors) > 0)

    def test_language_detection(self):
        # Python detection
        res_py = self.operator.execute("def hello():\n    pass")
        self.assertTrue(res_py.success)
        lang_fact = next(f for f in res_py.facts if f["type"] == "code_language")
        self.assertEqual(lang_fact["language"], "python")

        # JS detection
        res_js = self.operator.execute("const a = 10;\nconsole.log(a);")
        self.assertTrue(res_js.success)
        lang_fact_js = next(f for f in res_js.facts if f["type"] == "code_language")
        self.assertEqual(lang_fact_js["language"], "javascript")

    def test_python_syntax_valid(self):
        res = self.operator.execute("```python\ndef calculate_value(x, y):\n    return x + y\n```")
        self.assertTrue(res.success)
        
        syntax_fact = next(f for f in res.facts if f["type"] == "syntax_check")
        self.assertTrue(syntax_fact["valid"])
        self.assertEqual(syntax_fact["language"], "python")

    def test_python_syntax_invalid(self):
        # Python missing paren
        res = self.operator.execute("def calculate_value(x, y:\n    return x + y")
        self.assertTrue(res.success)
        
        syntax_fact = next(f for f in res.facts if f["type"] == "syntax_check")
        self.assertFalse(syntax_fact["valid"])
        self.assertEqual(syntax_fact["language"], "python")
        self.assertIn("SyntaxError", syntax_fact["error"])
        self.assertEqual(syntax_fact["line"], 1)

        # Python indentation error
        res_indent = self.operator.execute("def run():\nprint('hi')")
        self.assertTrue(res_indent.success)
        
        syntax_fact_indent = next(f for f in res_indent.facts if f["type"] == "syntax_check")
        self.assertFalse(syntax_fact_indent["valid"])
        self.assertIn("indent", syntax_fact_indent["error"].lower())
        
        bug_fact = next(f for f in res_indent.facts if f["type"] == "bug_category")
        self.assertEqual(bug_fact["category"], "indentation")

    def test_mismatched_brackets_generic(self):
        # JavaScript missing closing curly brace
        res = self.operator.execute("```javascript\nfunction myFunc() {\n   console.log('hello');\n```")
        self.assertTrue(res.success)
        
        syntax_fact = next(f for f in res.facts if f["type"] == "syntax_check")
        self.assertFalse(syntax_fact["valid"])
        self.assertEqual(syntax_fact["language"], "javascript")
        self.assertIn("Unmatched open bracket", syntax_fact["error"])
        
        bug_fact = next(f for f in res.facts if f["type"] == "bug_category")
        self.assertEqual(bug_fact["category"], "mismatched_brackets")

    def test_bug_heuristics(self):
        # Python missing colon
        res = self.operator.execute("def check_val(x)\n    return x")
        self.assertTrue(res.success)
        
        bug_fact = next(f for f in res.facts if f["type"] == "bug_category")
        self.assertEqual(bug_fact["category"], "missing_colon")
        self.assertEqual(bug_fact["line"], 1)

        # JS assignment in condition
        res_js = self.operator.execute("```js\nif (x = 5) {\n    console.log(x);\n}\n```")
        self.assertTrue(res_js.success)
        bug_fact_js = next(f for f in res_js.facts if f["type"] == "bug_category")
        self.assertEqual(bug_fact_js["category"], "assignment_in_condition")

if __name__ == "__main__":
    unittest.main()
