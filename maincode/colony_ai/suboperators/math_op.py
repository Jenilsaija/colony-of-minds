"""
Math specialist suboperator.
Safely evaluates arithmetic expressions using Python's AST (Abstract Syntax Tree) module.
Avoids unsafe raw eval() to prevent remote code execution vulnerabilities.
"""

import ast
import json
import operator
import re
from typing import Union, List, Dict, Any, Optional
from colony.operator import BaseSuboperator
from colony.schemas import SuboperatorResponse

OPERATOR_INFO = {
    "name": "math_op",
    "version": "0.1.0",
    "capabilities": ["arithmetic", "percentage"],
    "cost": "low",
    "safe_for_parallel": True
}


class SafeCalculator:
    """
    Evaluator that only parses and computes simple math AST nodes.
    """
    # Map AST binary operations to operator functions
    _BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    # Map AST unary operations to operator functions
    _UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(self, expression: str) -> Union[int, float]:
        """
        Parse and evaluate an arithmetic string expression.
        """
        try:
            tree = ast.parse(expression.strip(), mode="eval")
            return self._eval_node(tree.body)
        except (ZeroDivisionError, ValueError, TypeError):
            raise
        except Exception as e:
            raise ValueError(f"Safe calculator could not evaluate expression '{expression}': {e}")

    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        # Constants/Literal numbers
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError(f"Invalid constant type: {type(node.value)}")
        elif type(node).__name__ == "Num":  # Fallback for Python versions < 3.8
            return node.n
            
        # Binary Operations (e.g. 5 + 3)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._BIN_OPS:
                raise TypeError(f"Unsupported binary operator: {op_type.__name__}")
            
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            
            # Check for division by zero
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division or modulo by zero is not allowed.")
                
            # Restrict exponentiation size to prevent resource exhaustion attacks (infinite hangs)
            if op_type == ast.Pow:
                if abs(left) > 10000 or abs(right) > 100:
                    raise ValueError("Exponentiation base or power is too large (safety threshold).")
                    
            return self._BIN_OPS[op_type](left, right)
            
        # Unary Operations (e.g. -5)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._UNARY_OPS:
                raise TypeError(f"Unsupported unary operator: {op_type.__name__}")
                
            operand = self._eval_node(node.operand)
            return self._UNARY_OPS[op_type](operand)
            
        else:
            raise TypeError(f"Unsupported operation structure: {type(node).__name__}")


class MathOperator(BaseSuboperator):
    """
    Math suboperator handles calculation requests.
    """

    @property
    def name(self) -> str:
        return "math_op"

    def execute(self, query: str, context: Optional[dict] = None) -> SuboperatorResponse:
        """
        Extract expression from query, evaluate it, and return formatted facts.
        """
        expression = self._extract_expression(query)
        if not expression:
            return SuboperatorResponse(
                operator=self.name,
                success=False,
                confidence=0.0,
                errors=["No math expression could be extracted from query."]
            )

        # Check if the query explicitly specifies using the tool
        use_tool = "tool" in query.lower()
        if use_tool:
            try:
                from colony.tools import TOOL_REGISTRY
            except ImportError:
                from colony_ai.colony.tools import TOOL_REGISTRY
            
            tool = TOOL_REGISTRY.get_tool("calculator")
            if not tool:
                return SuboperatorResponse.create_error(
                    self.name, "Calculator tool not found in registry."
                )
            
            tool_log = tool.execute(expression, context)
            
            # Print the tool log JSON as specified in success criteria
            print("Tool log:")
            print(json.dumps({
                "tool": tool_log["tool"],
                "input": tool_log["input"],
                "output": tool_log["output"],
                "success": tool_log["success"]
            }, indent=2))
            
            if tool_log["success"]:
                return SuboperatorResponse(
                    operator=self.name,
                    success=True,
                    confidence=1.0,
                    facts=[
                        {
                            "type": "tool_call",
                            "tool": "calculator",
                            "input": expression,
                            "output": tool_log["output"],
                            "success": True,
                            "duration_ms": tool_log.get("duration_ms", 0)
                        },
                        {
                            "type": "calculation",
                            "expression": expression,
                            "result": tool_log["output"],
                            "method": "tool_calculator"
                        }
                    ]
                )
            else:
                return SuboperatorResponse.create_error(
                    self.name, f"Tool execution failed: {tool_log.get('output')}"
                )

        calculator = SafeCalculator()
        try:
            result = calculator.evaluate(expression)
            return SuboperatorResponse(
                operator=self.name,
                success=True,
                confidence=1.0,
                facts=[{
                    "type": "calculation",
                    "expression": expression,
                    "result": result,
                    "method": "safe_arithmetic_eval"
                }]
            )
        except Exception as e:
            return SuboperatorResponse(
                operator=self.name,
                success=False,
                confidence=0.0,
                errors=[str(e)]
            )

    def _extract_expression(self, query: str) -> str:
        """
        Extract the mathematical expression from user query.
        """
        query_clean = query.strip()
        
        # Check for percentage pattern, e.g. "18% GST on 25000" or "15% of 200"
        pct_match = re.search(
            r"(\d+(?:\.\d+)?)\s*%\s*(?:gst\s+)?(?:on|of)\s+(\d+(?:\.\d+)?)",
            query_clean,
            re.IGNORECASE
        )
        if pct_match:
            pct_val = pct_match.group(1)
            base_val = pct_match.group(2)
            return f"({pct_val} / 100) * {base_val}"

        # Check command prefixes
        for prefix in ["calculate", "calc", "math"]:
            if prefix in query_clean.lower():
                idx = query_clean.lower().find(prefix) + len(prefix)
                expr = query_clean[idx:].strip()
                expr = expr.lstrip(":=").rstrip("?").strip()
                if expr:
                    # If suffix contains conversational words, isolate mathematical substring
                    if re.search(r"[a-zA-Z]{2,}", expr):
                        matches = re.findall(r"[\d\+\-\*\/\(\)\s\.\%\/\/]+", expr)
                        if matches:
                            valid_matches = [m.strip() for m in matches if any(c.isdigit() for c in m)]
                            if valid_matches:
                                return max(valid_matches, key=len)
                    return expr

        # Fallback: find the longest mathematical character sequence with at least one digit
        matches = re.findall(r"[\d\+\-\*\/\(\)\s\.\%\/\/]+", query_clean)
        if matches:
            valid_matches = [m.strip() for m in matches if any(c.isdigit() for c in m)]
            if valid_matches:
                return max(valid_matches, key=len)
                
        return ""
