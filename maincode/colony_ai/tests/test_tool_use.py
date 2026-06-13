import unittest
import os
import tempfile
import time
from colony.tools import TOOL_REGISTRY, CalculatorTool, DateTimeTool, FileReaderTool, WebFetcherTool, ShellRunnerTool, FileDeleterTool
from colony.verifier import Verifier
from colony.router import Router
from run_colony import run_pipeline


class TestToolUse(unittest.TestCase):
    def setUp(self):
        self.verifier = Verifier()
        self.router = Router()
        # Create a temp file for read/delete tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file_path = os.path.join(self.temp_dir.name, "test_file.txt")
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("Colony test content.")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_registry_has_standard_tools(self):
        tools = TOOL_REGISTRY.list_tools()
        self.assertIn("calculator", tools)
        self.assertIn("datetime", tools)
        self.assertIn("file_reader", tools)
        self.assertIn("web_fetcher", tools)
        self.assertIn("shell_runner", tools)
        self.assertIn("file_deleter", tools)

    def test_calculator_tool_execution(self):
        calc_tool = TOOL_REGISTRY.get_tool("calculator")
        self.assertIsNotNone(calc_tool)
        res = calc_tool.execute("45 * 123")
        self.assertTrue(res["success"])
        self.assertEqual(res["output"], 5535)
        self.assertEqual(res["tool"], "calculator")

    def test_datetime_tool_execution(self):
        dt_tool = TOOL_REGISTRY.get_tool("datetime")
        res = dt_tool.execute("")
        self.assertTrue(res["success"])
        self.assertIn("T", res["output"])  # ISO format check

    def test_file_reader_tool_execution(self):
        reader_tool = TOOL_REGISTRY.get_tool("file_reader")
        res = reader_tool.execute(self.temp_file_path)
        self.assertTrue(res["success"])
        self.assertEqual(res["output"], "Colony test content.")
        self.assertEqual(res["path"], os.path.abspath(self.temp_file_path))
        self.assertIn("timestamp", res)

    def test_web_fetcher_tool_execution(self):
        fetcher_tool = TOOL_REGISTRY.get_tool("web_fetcher")
        # Test with a mock output or quick request
        res = fetcher_tool.execute("https://example.com")
        self.assertTrue(res["success"])
        self.assertIn("source_url", res)
        self.assertEqual(res["source_url"], "https://example.com")
        self.assertTrue(len(res["output"]) > 0)

    def test_shell_runner_denial_by_default(self):
        # Without bypass context, high-risk shell runner should default to abort in non-interactive environment
        shell_tool = TOOL_REGISTRY.get_tool("shell_runner")
        res = shell_tool.execute("echo hello")
        self.assertFalse(res["success"])
        self.assertIn("Aborted", res["output"])

    def test_shell_runner_with_bypass_confirmation(self):
        shell_tool = TOOL_REGISTRY.get_tool("shell_runner")
        res = shell_tool.execute("echo hello", {"bypass_confirmation": True})
        self.assertTrue(res["success"])
        self.assertEqual(res["output"], "hello")
        self.assertEqual(res["exit_code"], 0)

    def test_file_deleter_with_bypass_confirmation(self):
        deleter_tool = TOOL_REGISTRY.get_tool("file_deleter")
        # Ensure file exists
        self.assertTrue(os.path.exists(self.temp_file_path))
        res = deleter_tool.execute(self.temp_file_path, {"bypass_confirmation": True})
        self.assertTrue(res["success"])
        self.assertFalse(os.path.exists(self.temp_file_path))

    def test_verifier_inspects_tool_results_correctly(self):
        # Calculator verification
        fact_calc = {
            "type": "tool_call",
            "tool": "calculator",
            "input": "45 * 123",
            "output": 5535,
            "success": True
        }
        is_valid, _ = self.verifier._verify_tool_call(fact_calc)
        self.assertTrue(is_valid)

        # Web fetcher verification
        fact_web_ok = {
            "type": "tool_call",
            "tool": "web_fetcher",
            "input": "https://example.com",
            "output": "content",
            "source_url": "https://example.com",
            "success": True
        }
        is_valid, _ = self.verifier._verify_tool_call(fact_web_ok)
        self.assertTrue(is_valid)

        fact_web_bad = {
            "type": "tool_call",
            "tool": "web_fetcher",
            "input": "https://example.com",
            "output": "content",
            "success": True
        }
        is_valid, err = self.verifier._verify_tool_call(fact_web_bad)
        self.assertFalse(is_valid)
        self.assertIn("missing required source URL", err)

        # Shell runner verification
        fact_shell_ok = {
            "type": "tool_call",
            "tool": "shell_runner",
            "input": "echo hello",
            "output": "hello",
            "exit_code": 0,
            "success": True
        }
        is_valid, _ = self.verifier._verify_tool_call(fact_shell_ok)
        self.assertTrue(is_valid)

        fact_shell_bad = {
            "type": "tool_call",
            "tool": "shell_runner",
            "input": "echo hello",
            "output": "hello",
            "success": True
        }
        is_valid, err = self.verifier._verify_tool_call(fact_shell_bad)
        self.assertFalse(is_valid)
        self.assertIn("missing required exit code", err)

        # File reader verification
        fact_file_ok = {
            "type": "tool_call",
            "tool": "file_reader",
            "input": "test.txt",
            "output": "content",
            "path": "test.txt",
            "timestamp": "2026-06-09T07:28:12",
            "success": True
        }
        is_valid, _ = self.verifier._verify_tool_call(fact_file_ok)
        self.assertTrue(is_valid)

        fact_file_bad = {
            "type": "tool_call",
            "tool": "file_reader",
            "input": "test.txt",
            "output": "content",
            "path": "test.txt",
            "success": True
        }
        is_valid, err = self.verifier._verify_tool_call(fact_file_bad)
        self.assertFalse(is_valid)
        self.assertIn("missing required timestamp", err)

    def test_router_selects_tool_op(self):
        res = self.router.route("read file my_config.json")
        self.assertIn("tool_op", res.selected_operators)

        res = self.router.route("fetch https://google.com")
        self.assertIn("tool_op", res.selected_operators)

        res = self.router.route("run command echo 'success'")
        self.assertIn("tool_op", res.selected_operators)

    def test_pipeline_with_calculator_tool(self):
        # End-to-end pipeline run mimicking success criteria
        ans = run_pipeline("Calculate 45 * 123 using tool.", verbose=True)
        self.assertIn("5535", ans)


if __name__ == "__main__":
    unittest.main()
