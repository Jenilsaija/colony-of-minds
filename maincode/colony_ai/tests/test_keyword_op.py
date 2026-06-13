"""
Unit tests for the KeywordOperator.
"""

import unittest
import sys
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from suboperators.keyword_op import KeywordOperator

class TestKeywordOp(unittest.TestCase):
    def setUp(self):
        self.operator = KeywordOperator()

    def test_name(self):
        self.assertEqual(self.operator.name, "keyword_op")

    def test_greetings_and_framework_keywords(self):
        # Test greeting
        res = self.operator.execute("hello, how are you?")
        self.assertTrue(res.success)
        self.assertEqual(res.confidence, 1.0)
        self.assertEqual(res.facts[0]["type"], "greeting")
        self.assertEqual(res.facts[0]["value"], "Welcome to the Colony")

        # Test framework keyword
        res = self.operator.execute("tell me about the colony minds")
        self.assertTrue(res.success)
        self.assertEqual(res.confidence, 0.95)
        fact_types = [f["type"] for f in res.facts]
        self.assertIn("keyword_match", fact_types)
        keywords = [f.get("keyword") for f in res.facts]
        self.assertIn("colony", keywords)
        self.assertIn("minds", keywords)

    def test_emails_and_urls_extraction(self):
        # Email
        res = self.operator.execute("Send the invoice to support@colony.ai please.")
        self.assertTrue(res.success)
        self.assertEqual(res.facts[0]["type"], "email")
        self.assertEqual(res.facts[0]["value"], "support@colony.ai")

        # URL
        res2 = self.operator.execute("Visit https://google.com or www.example.org/path.")
        self.assertTrue(res2.success)
        fact_values = [f["value"] for f in res2.facts if f["type"] == "url"]
        self.assertIn("https://google.com", fact_values)
        self.assertIn("www.example.org/path", fact_values)

    def test_number_and_date_extraction(self):
        # Numbers
        res = self.operator.execute("The total count is 45 and version is 1.25.")
        self.assertTrue(res.success)
        numbers = [f["value"] for f in res.facts if f["type"] == "number"]
        self.assertIn(45, numbers)
        self.assertIn(1.25, numbers)

        # Dates
        res2 = self.operator.execute("Submit on 2026-06-08 or by 12/25/2026.")
        self.assertTrue(res2.success)
        dates = [f["value"] for f in res2.facts if f["type"] == "date"]
        self.assertIn("2026-06-08", dates)
        self.assertIn("12/25/2026", dates)

    def test_language_and_intent_extraction(self):
        # Python language and compile intent
        res = self.operator.execute("Please compile this python script.")
        self.assertTrue(res.success)
        
        fact_types = [f["type"] for f in res.facts]
        self.assertIn("language", fact_types)
        self.assertIn("intent_word", fact_types)

        languages = [f["value"] for f in res.facts if f["type"] == "language"]
        intents = [f["value"] for f in res.facts if f["type"] == "intent_word"]
        self.assertIn("python", languages)
        self.assertIn("compile", intents)

    def test_help_keyword_matching(self):
        res = self.operator.execute("how can you help?")
        self.assertTrue(res.success)
        self.assertEqual(res.confidence, 0.95)
        self.assertEqual(res.facts[0]["type"], "keyword_match")
        self.assertEqual(res.facts[0]["keyword"], "help")
        self.assertIn("mathematics", res.facts[0]["value"].lower())

    def test_no_matches_fallback(self):
        res = self.operator.execute("xyz abc qwe rty")
        self.assertTrue(res.success)
        self.assertEqual(res.confidence, 0.1)
        self.assertEqual(len(res.facts), 0)

if __name__ == "__main__":
    unittest.main()
