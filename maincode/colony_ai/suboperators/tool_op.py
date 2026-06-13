"""
Tool Use suboperator.
Parses query triggers for different tool commands and executes them.
"""

import json
from typing import Optional
from colony.operator import BaseSuboperator
from colony.schemas import SuboperatorResponse

try:
    from colony.tools import TOOL_REGISTRY
except ImportError:
    try:
        from colony_ai.colony.tools import TOOL_REGISTRY
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).resolve().parent.parent))
        from colony.tools import TOOL_REGISTRY


class ToolOperator(BaseSuboperator):
    """
    Handles general tool routing and execution.
    """
    @property
    def name(self) -> str:
        return "tool_op"

    def execute(self, query: str, context: Optional[dict] = None) -> SuboperatorResponse:
        query_clean = query.strip()
        query_lower = query_clean.lower()

        # Parse command and argument
        tool_name = None
        tool_input = None

        if "read file" in query_lower:
            tool_name = "file_reader"
            tool_input = self._extract_arg(query_clean, "read file")
        elif "file_reader" in query_lower:
            tool_name = "file_reader"
            tool_input = self._extract_arg(query_clean, "file_reader")
        elif "fetch" in query_lower:
            tool_name = "web_fetcher"
            tool_input = self._extract_arg(query_clean, "fetch")
        elif "web_fetcher" in query_lower:
            tool_name = "web_fetcher"
            tool_input = self._extract_arg(query_clean, "web_fetcher")
        elif "delete file" in query_lower:
            tool_name = "file_deleter"
            tool_input = self._extract_arg(query_clean, "delete file")
        elif "file_deleter" in query_lower:
            tool_name = "file_deleter"
            tool_input = self._extract_arg(query_clean, "file_deleter")
        elif "run command" in query_lower:
            tool_name = "shell_runner"
            tool_input = self._extract_arg(query_clean, "run command")
        elif "shell_runner" in query_lower:
            tool_name = "shell_runner"
            tool_input = self._extract_arg(query_clean, "shell_runner")
        elif "current time" in query_lower or "datetime" in query_lower:
            tool_name = "datetime"
            tool_input = ""

        if not tool_name:
            return SuboperatorResponse.create_error(
                self.name, "Could not determine which tool to execute from query."
            )

        tool = TOOL_REGISTRY.get_tool(tool_name)
        if not tool:
            return SuboperatorResponse.create_error(
                self.name, f"Tool '{tool_name}' not found in registry."
            )

        # Execute the tool
        tool_log = tool.execute(tool_input, context)

        # Print the tool log JSON as specified in success criteria
        print("Tool log:")
        print(json.dumps({
            "tool": tool_log["tool"],
            "input": tool_log["input"],
            "output": tool_log["output"],
            "success": tool_log["success"]
        }, indent=2))

        if tool_log["success"]:
            # Standardize tool log format inside facts list
            fact = {
                "type": "tool_call",
                "tool": tool_name,
                "input": tool_input,
                "output": tool_log["output"],
                "success": True,
                "duration_ms": tool_log.get("duration_ms", 0)
            }
            # Copy other properties like path, timestamp, source_url, exit_code
            for k in ("path", "timestamp", "source_url", "exit_code"):
                if k in tool_log:
                    fact[k] = tool_log[k]
                    
            return SuboperatorResponse(
                operator=self.name,
                success=True,
                confidence=1.0,
                facts=[fact]
            )
        else:
            return SuboperatorResponse.create_error(
                self.name, f"Tool execution failed: {tool_log.get('output')}"
            )

    def _extract_arg(self, query: str, prefix: str) -> str:
        """Helper to extract and clean argument after a prefix."""
        idx = query.lower().find(prefix.lower())
        arg = query[idx + len(prefix):].strip()
        # strip optional separator chars, e.g., :, =, and quotes
        arg = arg.lstrip(":=").strip()
        if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
            arg = arg[1:-1].strip()
        return arg
