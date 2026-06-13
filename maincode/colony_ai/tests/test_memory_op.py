"""
Unit tests for the Colony Memory Suboperator and MemoryStore.
"""

import unittest
import os
import sqlite3
import sys
from pathlib import Path

# Setup paths so tests can run from anywhere
sys.path.append(str(Path(__file__).resolve().parent.parent))

from memory.memory_store import MemoryStore
from suboperators.memory_op import MemoryOperator
from colony.schemas import SuboperatorResponse

class TestMemoryOp(unittest.TestCase):
    def setUp(self):
        # Use a temporary database for testing
        self.test_db_path = "test_colony_memory_op.db"
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except PermissionError:
                pass
        
        # Override default database path environment variable
        os.environ["COLONY_MEMORY_DB_PATH"] = self.test_db_path
        self.memory_store = MemoryStore(self.test_db_path)
        self.operator = MemoryOperator()

    def tearDown(self):
        # Clean up database file
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except PermissionError:
                pass

    def test_db_initialization(self):
        # Verify tables exist
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            self.assertIn("facts", tables)
            self.assertIn("preferences", tables)
            self.assertIn("interactions", tables)
            self.assertIn("interaction_log", tables)

    def test_store_and_get_fact(self):
        self.memory_store.store_fact("project_type", "open_source")
        fact = self.memory_store.get_fact("project_type")
        self.assertIsNotNone(fact)
        self.assertEqual(fact["value"], "open_source")

    def test_store_and_get_preference(self):
        self.memory_store.store_preference("user_name", "Alice")
        pref = self.memory_store.get_preference("user_name")
        self.assertIsNotNone(pref)
        self.assertEqual(pref["value"], "Alice")

    def test_execute_save_preference(self):
        query = "Remember my project name is OpenPrompt."
        response = self.operator.execute(query)
        self.assertTrue(response.success)
        self.assertEqual(len(response.facts), 1)
        self.assertEqual(response.facts[0]["type"], "stored_preference")
        self.assertEqual(response.facts[0]["key"], "project_name")
        self.assertEqual(response.facts[0]["value"], "OpenPrompt")

        # Double check DB directly
        pref = self.memory_store.get_preference("project_name")
        self.assertIsNotNone(pref)
        self.assertEqual(pref["value"], "OpenPrompt")

    def test_execute_retrieve_preference_success(self):
        # First save preference
        self.memory_store.store_preference("project_name", "OpenPrompt")
        
        query = "What is my project name?"
        response = self.operator.execute(query)
        self.assertTrue(response.success)
        self.assertEqual(len(response.facts), 1)
        self.assertEqual(response.facts[0]["type"], "retrieved_preference")
        self.assertEqual(response.facts[0]["key"], "project_name")
        self.assertEqual(response.facts[0]["value"], "OpenPrompt")

    def test_execute_retrieve_preference_not_found(self):
        query = "What is my favorite food?"
        response = self.operator.execute(query)
        self.assertTrue(response.success)
        self.assertEqual(len(response.facts), 1)
        self.assertEqual(response.facts[0]["type"], "preference_not_found")
        self.assertEqual(response.facts[0]["key"], "favorite_food")

    def test_execute_contextual_search(self):
        # Store a fact
        self.memory_store.store_fact("framework_language", "Python")
        
        # General query that does not explicitly ask to store or retrieve, but contains keyword
        query = "This framework_language is awesome."
        response = self.operator.execute(query)
        self.assertTrue(response.success)
        self.assertEqual(len(response.facts), 1)
        self.assertEqual(response.facts[0]["type"], "memory_context")
        self.assertEqual(response.facts[0]["key"], "framework_language")
        self.assertEqual(response.facts[0]["value"], "Python")

if __name__ == "__main__":
    unittest.main()
