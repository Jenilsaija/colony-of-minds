"""
Verifier component for checking the validity and safety of suboperator responses.
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Union

from colony.schemas import SuboperatorResponse, VerificationResult
from colony.config import DEFAULT_CONFIDENCE_THRESHOLD

# Robust imports of SafeCalculator to handle execution environments
try:
    from suboperators.math_op import SafeCalculator
except ImportError:
    try:
        from colony_ai.suboperators.math_op import SafeCalculator
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).resolve().parent.parent))
        from suboperators.math_op import SafeCalculator


class Verifier:
    """
    Enforces quality control, validating structured data outputs from suboperators
    before they are passed to the Atma voice synthesizer.
    """

    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold

    def verify(self, response: SuboperatorResponse) -> bool:
        """
        Validates if a response is acceptable individually.
        Checks success, errors, confidence threshold, empty facts, schema, and recomputes math.
        
        Args:
            response: The SuboperatorResponse from a specialist.
            
        Returns:
            True if response is valid and meets safety/correctness bars, else False.
        """
        # Reject if execution failed
        if not response.success:
            return False
            
        # Reject if error messages are logged
        if response.errors:
            return False
            
        # Reject if confidence score is below threshold
        if response.confidence < self.confidence_threshold:
            return False
            
        # Reject if facts list is empty (Reject empty outputs)
        if not response.facts:
            return False

        # Validate schema and math recomputation of each fact
        for fact in response.facts:
            if not self._validate_fact_schema(fact):
                return False
                
            if fact.get("type") == "calculation":
                is_valid, _ = self._verify_math_fact(fact)
                if not is_valid:
                    return False
                    
            if fact.get("type") == "tool_call":
                is_valid, _ = self._verify_tool_call(fact)
                if not is_valid:
                    return False
                    
        return True

    def verify_all(
        self, 
        responses: List[SuboperatorResponse], 
        query: str = "", 
        routed_operators: Optional[List[str]] = None
    ) -> VerificationResult:
        """
        Performs full verification on multiple responses, resolving contradictions,
        detecting missing information, validating schemas, and recomputing facts.
        
        Args:
            responses: List of SuboperatorResponses.
            query: The original user query.
            routed_operators: List of operators that were intended to execute.
            
        Returns:
            A VerificationResult bundle containing verified facts, rejected facts,
            warnings, and missing details.
        """
        verified_facts: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        warnings: List[str] = []
        missing: List[str] = []

        # 1. Individual response validation & warning detection
        for resp in responses:
            if not resp.success:
                rejected.append({
                    "operator": resp.operator,
                    "reason": f"Execution failed. Errors: {resp.errors}"
                })
                continue
                
            if resp.confidence < self.confidence_threshold:
                rejected.append({
                    "operator": resp.operator,
                    "reason": f"Confidence {resp.confidence:.2f} below threshold {self.confidence_threshold:.2f}"
                })
                continue
                
            if not resp.facts:
                rejected.append({
                    "operator": resp.operator,
                    "reason": "Empty facts list (rejected empty output)."
                })
                continue

            # Confidence warnings (usable with warning threshold: 0.70 to 0.89)
            if self.confidence_threshold <= resp.confidence < 0.90:
                warnings.append(
                    f"Operator '{resp.operator}' returned confidence {resp.confidence:.2f} (usable with warning threshold)."
                )

            # Fact level validation
            for fact in resp.facts:
                # Validate schema
                if not self._validate_fact_schema(fact):
                    rejected.append({
                        "operator": resp.operator,
                        "fact": fact,
                        "reason": "Schema validation failed."
                    })
                    continue

                # Math validation
                if fact.get("type") == "calculation":
                    is_valid, err_msg = self._verify_math_fact(fact)
                    if not is_valid:
                        rejected.append({
                            "operator": resp.operator,
                            "fact": fact,
                            "reason": err_msg
                        })
                        continue

                # Tool call validation
                if fact.get("type") == "tool_call":
                    is_valid, err_msg = self._verify_tool_call(fact)
                    if not is_valid:
                        rejected.append({
                            "operator": resp.operator,
                            "fact": fact,
                            "reason": err_msg
                        })
                        continue

                # Collect verified fact
                fact_copy = dict(fact)
                fact_copy["operator"] = resp.operator
                fact_copy["response_confidence"] = resp.confidence
                verified_facts.append(fact_copy)

        # 2. Contradiction Detection between operators (e.g. language contradictions)
        lang_facts = []
        for fact in verified_facts:
            ftype = fact.get("type")
            if ftype == "language":
                lang_facts.append({
                    "val": fact.get("value", ""),
                    "conf": fact.get("response_confidence", 0.5),
                    "op": fact.get("operator", ""),
                    "original": fact
                })
            elif ftype == "code_language":
                lang_facts.append({
                    "val": fact.get("language", ""),
                    "conf": fact.get("confidence", fact.get("response_confidence", 0.5)),
                    "op": fact.get("operator", ""),
                    "original": fact
                })

        distinct_langs = {lf["val"].lower() for lf in lang_facts if lf["val"]}
        if len(distinct_langs) > 1:
            # Sort by confidence descending
            lang_facts.sort(key=lambda x: (x["conf"], x["op"]), reverse=True)
            winner = lang_facts[0]
            winner_lang = winner["val"]
            winner_op = winner["op"]

            resolved_facts = []
            for fact in verified_facts:
                ftype = fact.get("type")
                is_lang_fact = ftype in ("language", "code_language")
                if is_lang_fact:
                    val = fact.get("value") if ftype == "language" else fact.get("language")
                    if val and val.lower() == winner_lang.lower() and fact.get("operator") == winner_op:
                        resolved_facts.append(fact)
                    else:
                        rejected.append({
                            "operator": fact.get("operator"),
                            "fact": fact,
                            "reason": f"Contradiction: Discarded language '{val}' in favor of '{winner_lang}' from '{winner_op}' (higher confidence)."
                        })
                        warnings.append(
                            f"Contradiction resolved: Chosen language '{winner_lang}' ({winner_op}, confidence {winner['conf']}) over '{val}' ({fact.get('operator')}, confidence {fact.get('response_confidence')})."
                        )
                else:
                    resolved_facts.append(fact)
            verified_facts = resolved_facts

        # 3. Missing Information detection
        if routed_operators:
            for op in routed_operators:
                op_facts = [f for f in verified_facts if f.get("operator") == op]
                if not op_facts:
                    missing.append(f"No verified facts from routed operator '{op}'.")

        if query:
            query_lower = query.lower()
            # If math patterns or keywords are present in query but no calculation facts verified
            has_math_keywords = any(kw in query_lower for kw in ["calculate", "compute", "sum", "multiply", "subtract", "divide", "add", "math", "calc", "%"])
            has_math_pattern = bool(re.search(r"\d+\s*[\+\-\*\/\%]\s*\d+", query_lower))
            if (has_math_keywords or has_math_pattern) and not any(f.get("type") == "calculation" for f in verified_facts):
                if not any("calculation" in m for m in missing):
                    missing.append("calculation results (math_op)")

            # If code keywords are present in query but no code facts verified
            has_code_keywords = any(kw in query_lower for kw in ["code", "bug", "syntax", "function", "python", "javascript", "java", "c++", "programming", "script"])
            if has_code_keywords and not any(f.get("type") in ("code_language", "syntax_check", "bug_category") for f in verified_facts):
                if not any("code syntax" in m for m in missing):
                    missing.append("code syntax or language details (code_op)")

        # Clear temporary helper fields from final verified facts
        for f in verified_facts:
            f.pop("response_confidence", None)

        # verified is True if we successfully verified at least one fact and no fatal errors blocked execution
        verified = len(verified_facts) > 0

        # If we had routed operators but couldn't verify anything, it is not verified
        if routed_operators and not verified_facts:
            verified = False

        return VerificationResult(
            verified=verified,
            facts=verified_facts,
            rejected=rejected,
            warnings=warnings,
            missing=missing
        )

    def _validate_fact_schema(self, fact: Any) -> bool:
        """Checks if a fact dictionary conforms to expected schemas."""
        if not isinstance(fact, dict):
            return False
        if "type" not in fact or not isinstance(fact["type"], str):
            return False
        
        fact_type = fact["type"]
        if fact_type == "calculation":
            return (
                "expression" in fact 
                and isinstance(fact["expression"], str) 
                and "result" in fact 
                and isinstance(fact["result"], (int, float))
            )
        elif fact_type == "code_language":
            return (
                "language" in fact 
                and isinstance(fact["language"], str)
            )
        elif fact_type == "syntax_check":
            return (
                "language" in fact 
                and isinstance(fact["language"], str) 
                and "valid" in fact 
                and isinstance(fact["valid"], bool)
            )
        elif fact_type == "bug_category":
            return (
                "category" in fact 
                and isinstance(fact["category"], str) 
                and "description" in fact 
                and isinstance(fact["description"], str)
            )
        elif fact_type == "plan":
            return (
                "steps" in fact 
                and isinstance(fact["steps"], list)
            )
        elif fact_type == "tool_call":
            return (
                "tool" in fact 
                and "input" in fact
                and "success" in fact
            )
        return True

    def _verify_math_fact(self, fact: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Recomputes a mathematical calculation fact independently using SafeCalculator.
        Returns (is_valid, error_message).
        """
        expression = fact.get("expression")
        expected_result = fact.get("result")
        
        if expression is None or expected_result is None:
            return False, "Calculation fact missing expression or result."
            
        try:
            calculator = SafeCalculator()
            computed_result = calculator.evaluate(expression)
            
            if isinstance(computed_result, (int, float)) and isinstance(expected_result, (int, float)):
                if abs(computed_result - expected_result) < 1e-9:
                    return True, None
                else:
                    return False, f"Math verification failed: expected {computed_result}, got {expected_result}"
            else:
                return False, f"Recomputed value '{computed_result}' is not a numeric type."
        except Exception as e:
            return False, f"Failed to recompute expression '{expression}': {e}"

    def _verify_tool_call(self, fact: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates a tool_call fact against safety and tool-specific constraints.
        Returns (is_valid, error_message).
        """
        tool_name = fact.get("tool")
        success = fact.get("success", False)
        output = fact.get("output")

        if not success:
            return False, f"Tool execution for '{tool_name}' failed."

        if tool_name == "calculator":
            # Calculator result can be trusted high-confidence, but let's double check if numeric
            if not isinstance(output, (int, float)):
                return False, f"Calculator output '{output}' is not numeric."
            return True, None

        elif tool_name == "web_fetcher":
            # Web result needs source URL
            source_url = fact.get("source_url")
            if not source_url:
                return False, "Web fetcher result is missing required source URL."
            return True, None

        elif tool_name == "shell_runner":
            # Shell output needs exit code
            exit_code = fact.get("exit_code")
            if exit_code is None:
                return False, "Shell runner result is missing required exit code."
            return True, None

        elif tool_name == "file_reader":
            # File read needs path and timestamp
            path = fact.get("path")
            timestamp = fact.get("timestamp")
            if not path:
                return False, "File reader result is missing required path."
            if not timestamp:
                return False, "File reader result is missing required timestamp."
            return True, None

        elif tool_name in ("file_deleter", "datetime"):
            return True, None

        return False, f"Unknown tool '{tool_name}' encountered."

