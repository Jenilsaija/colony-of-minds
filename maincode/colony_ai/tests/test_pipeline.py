"""
Integration tests for the end-to-end Colony of Minds pipeline.
"""

import unittest
import sys
import os
import sqlite3
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from run_colony import run_pipeline
from memory.memory_store import MemoryStore

class TestPipeline(unittest.TestCase):
    def setUp(self):
        # Use a temporary database for testing
        self.test_db_path = "test_colony_memory.db"
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except PermissionError:
                pass  # Ignore lock, we will clear the table instead
        
        # Override default database path environment variable
        os.environ["COLONY_MEMORY_DB_PATH"] = self.test_db_path
        self.memory = MemoryStore(self.test_db_path)
        
        # Ensure database is clean by truncating the interaction log table
        with sqlite3.connect(self.test_db_path) as conn:
            conn.execute("DELETE FROM interaction_log")
            conn.commit()

    def tearDown(self):
        # Clean up database file
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except PermissionError:
                pass  # Ignore if file lock is still active

    def test_greeting_pipeline(self):
        response = run_pipeline("hello colony", verbose=True)
        # Check synthesized response text
        self.assertIn("Welcome to the Colony", response)
        
        # Verify db persistence
        history = self.memory.get_history(5)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["query"], "hello colony")
        self.assertIn("Welcome to the Colony", history[0]["response"])
        self.assertEqual(history[0]["routed_operators"], ["keyword_op"])
        self.assertTrue(history[0]["verified"])

    def test_math_pipeline(self):
        response = run_pipeline("calculate 45 * 123", verbose=True)
        # Check math output format
        self.assertIn("45 * 123 = 5535", response)

        # Verify db persistence
        history = self.memory.get_history(5)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["query"], "calculate 45 * 123")
        self.assertIn("5535", history[0]["response"])
        self.assertEqual(history[0]["routed_operators"], ["math_op"])
        self.assertTrue(history[0]["verified"])

        # Test percentage pipeline execution
        response2 = run_pipeline("Calculate 18% GST on 25000 and write a short explanation.", verbose=True)
        self.assertIn("4500.0", response2)

    def test_fallback_no_match_pipeline(self):
        # A query that doesn't trigger any keyword or math
        response = run_pipeline("something totally random", verbose=True)
        # Verifier should reject keyword_op response because confidence will be 0.1 (< 0.5 threshold)
        self.assertIn("I could not find enough verified information to answer safely", response)
        
        # Check logs
        history = self.memory.get_history(5)
        self.assertEqual(len(history), 1)
        self.assertFalse(history[0]["verified"])

if __name__ == "__main__":
    unittest.main()
