"""
Atma voice synthesizer.
Constructs natural language answers from verified structured facts using templates or a local tiny model.
"""

import ast
import re
import json
import subprocess
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Union
from colony_ai.colony.schemas import SuboperatorResponse
from colony_ai.colony.config import DEFAULT_OLLAMA_PATH, DEFAULT_OLLAMA_MODEL, OLLAMA_NUM_THREADS, DEFAULT_OLLAMA_API_URL





class Atma:
    """
    Atma acts as the mouth of the colony. It does not perform reasoning on its own;
    instead, it takes verified facts and synthesizes a user-friendly response.
    """

    def speak(
        self, 
        query: str, 
        verified_responses: List[SuboperatorResponse], 
        verbose: bool = False,
        verification_result: Optional[Any] = None,
        routed_operators: Optional[List[str]] = None,
        model_name: Optional[str] = None,
        ollama_path: Optional[str] = None,
        context: Optional[dict] = None,
        ollama_api_url: Optional[str] = None
    ) -> str:
        """
        Synthesize natural language response from verified facts using either a local
        tiny model (Ollama) or falls back to deterministic templates.
        
        Args:
            query: The original user query.
            verified_responses: List of responses that passed verification.
            verbose: If True, appends a debug output block and prints process logs.
            verification_result: Optional VerificationResult bundle context.
            routed_operators: Optional list of selected operators from Router.
            model_name: Optional model override.
            ollama_path: Optional ollama path override.
            context: Optional dict to capture execution metrics.
            ollama_api_url: Optional ollama api url override.
            
        Returns:
            A clean natural language answer string.
        """
        if context is None:
            context = {}

        if not verified_responses:
            ans = "I could not find enough verified information to answer safely. I detected the topic, but no reliable calculation or fact was produced."
            context["atma_mode"] = "template"
            if verbose:
                return ans + "\n\n" + self._generate_debug_block(
                    verified_responses, 
                    ans, 
                    verification_result, 
                    routed_operators
                )
            return ans

        # 1. Attempt Model Synthesis if a model is specified/available
        model = model_name or DEFAULT_OLLAMA_MODEL
        path = ollama_path or DEFAULT_OLLAMA_PATH
        api_url = ollama_api_url or DEFAULT_OLLAMA_API_URL
        
        model_output = None
        if model:
            # Flatten facts list and add operator metadata for model prompt context
            facts_list = []
            for resp in verified_responses:
                for fact in resp.facts:
                    fact_copy = dict(fact)
                    fact_copy["operator"] = resp.operator
                    facts_list.append(fact_copy)

            # Try HTTP API first
            model_output = self._call_ollama_api(query, facts_list, model, api_url, verbose)
            if model_output is None:
                # Fallback to CLI subprocess
                model_output = self._call_ollama(query, facts_list, model, path, verbose)

        # 2. Use Model Output or Fallback to Template synthesis
        if model_output is not None:
            ans = model_output
            context["atma_mode"] = "model"
        else:
            if model and verbose:
                print("[!] Model synthesis failed or unavailable. Falling back to Template Atma.")
            ans = self._speak_template(query, verified_responses)
            context["atma_mode"] = "template"

        if verbose:
            return ans + "\n\n" + self._generate_debug_block(
                verified_responses, 
                ans, 
                verification_result, 
                routed_operators
            )
        return ans

    def _call_ollama_api(
        self,
        query: str,
        facts: List[Dict[str, Any]],
        model: str,
        api_url: str,
        verbose: bool = False
    ) -> Optional[str]:
        """Runs the model using the Ollama HTTP API endpoint `/api/generate` (Option B)."""
        compressed_facts_str = self._compress_facts(facts)
        prompt = (
            "You are Atma, a synthesis engine.\n"
            "Use only VERIFIED_FACTS.\n"
            "Do not invent facts.\n"
            "If the facts are insufficient, say what is missing.\n"
            "Keep the answer concise and clear.\n\n"
            f"USER_PROMPT:\n{query}\n\n"
            f"VERIFIED_FACTS:\n{compressed_facts_str}\n\n"
            "FINAL_ANSWER:"
        )

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_thread": OLLAMA_NUM_THREADS,
                "temperature": 0.2,
                "num_ctx": 1024,
                "num_predict": 128
            }
        }

        try:
            url = f"{api_url.rstrip('/')}/api/generate"
            if verbose:
                print(f"[*] Calling model via Ollama HTTP API: {url}")
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, 
                data=data, 
                headers={"Content-Type": "application/json"}
            )
            # Timeout of 15 seconds to keep latency low and fall back quickly if server is unresponsive
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status == 200:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    output = resp_data.get("response", "").strip()
                    if output:
                        return output
        except Exception as e:
            if verbose:
                print(f"[!] Ollama HTTP API call failed: {e}. Falling back to CLI subprocess.")
        return None

    def _call_ollama(
        self, 
        query: str, 
        facts: List[Dict[str, Any]], 
        model: str, 
        path: str,
        verbose: bool = False
    ) -> Optional[str]:
        """Runs the model using the Ollama CLI subprocess pathway (Option A)."""
        compressed_facts_str = self._compress_facts(facts)
        prompt = (
            "You are Atma, a synthesis engine.\n"
            "Use only VERIFIED_FACTS.\n"
            "Do not invent facts.\n"
            "If the facts are insufficient, say what is missing.\n"
            "Keep the answer concise and clear.\n\n"
            f"USER_PROMPT:\n{query}\n\n"
            f"VERIFIED_FACTS:\n{compressed_facts_str}\n\n"
            "FINAL_ANSWER:"
        )

        try:
            command = [path, "run", model]
            if verbose:
                print(f"[*] Calling model via Ollama CLI: {' '.join(command)}")
            
            import os
            env = dict(os.environ)
            env["OMP_NUM_THREADS"] = str(OLLAMA_NUM_THREADS)
            env["OPENBLAS_NUM_THREADS"] = str(OLLAMA_NUM_THREADS)
            env["MKL_NUM_THREADS"] = str(OLLAMA_NUM_THREADS)
            env["VECLIB_MAXIMUM_THREADS"] = str(OLLAMA_NUM_THREADS)
            env["NUMEXPR_NUM_THREADS"] = str(OLLAMA_NUM_THREADS)
            
            # Use subprocess piping stdin to avoid CLI character limitations
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=45  # Timeout of 45 seconds to keep latency checked
            )

            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    return output
            else:
                if verbose:
                    print(f"[!] Ollama process failed with code {result.returncode}. Stderr: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            if verbose:
                print("[!] Ollama call timed out.")
            return None
        except Exception as e:
            if verbose:
                print(f"[!] Exception calling Ollama subprocess: {e}")
            return None

    def _speak_template(self, query: str, verified_responses: List[SuboperatorResponse]) -> str:
        """Fallback deterministic template speaker."""
        # Check if query requests explanation
        explain = "explain" in query.lower() or "explanation" in query.lower()

        answers = []
        for response in verified_responses:
            if response.operator == "math_op":
                answers.append(self._synthesize_math(response, explain))
            elif response.operator == "keyword_op":
                answers.append(self._synthesize_keyword(response))
            elif response.operator == "code_op":
                answers.append(self._synthesize_code(response))
            elif response.operator == "planner_op":
                answers.append(self._synthesize_planner(response))
            elif response.operator == "memory_op":
                answers.append(self._synthesize_memory(response))
            elif response.operator == "tool_op":
                answers.append(self._synthesize_tool(response))
            else:
                answers.append(self._synthesize_generic(response))

        # Filter out empty answers and join them
        answers = [ans for ans in answers if ans]
        if not answers:
            return "I could not find enough verified information to answer safely. I detected the topic, but no reliable calculation or fact was produced."
        return "\n\n".join(answers)

    def _synthesize_math(self, response: SuboperatorResponse, explain: bool) -> str:
        """Formats mathematical facts into structured strings."""
        parts = []
        for fact in response.facts:
            fact_type = fact.get("type")
            if fact_type == "calculation":
                expr = fact.get("expression")
                result = fact.get("result")
                if expr is not None and result is not None:
                    if explain:
                        parts.append(self._explain_calculation(expr, result))
                    else:
                        parts.append(f"{expr} = {result}.")
        if parts:
            return "\n".join(parts)
        return "Math operation succeeded, but no calculation facts were found."


    def _explain_calculation(self, expr: str, result: Union[int, float]) -> str:
        """Generates natural language explanations based on math operators."""
        clean_expr = expr.strip()
        
        # Check percentage pattern: e.g. "((18 / 100) * 25000)" or "(18 / 100) * 25000"
        pct_match = re.search(
            r"\(?(\d+(?:\.\d+)?)\s*/\s*100\)?\s*\*\s*(\d+(?:\.\d+)?)",
            clean_expr
        )
        if pct_match:
            pct = pct_match.group(1)
            base = pct_match.group(2)
            # Normalize float representation for clean output
            r_str = str(int(result)) if isinstance(result, float) and result.is_integer() else str(result)
            return f"{expr} = {result}. This means {pct}% of {base} gives {r_str}."

        # Parse basic arithmetic binary operations
        try:
            tree = ast.parse(clean_expr, mode="eval")
            node = tree.body
            if isinstance(node, ast.BinOp):
                left = self._get_ast_val(node.left)
                right = self._get_ast_val(node.right)
                op_type = type(node.op)
                
                op_words = {
                    ast.Add: "added to",
                    ast.Sub: "minus",
                    ast.Mult: "multiplied by",
                    ast.Div: "divided by",
                    ast.FloorDiv: "integer divided by",
                    ast.Mod: "modulo",
                    ast.Pow: "raised to the power of"
                }
                
                if op_type in op_words:
                    op_word = op_words[op_type]
                    # Format float representations cleanly
                    r_str = str(int(result)) if isinstance(result, float) and result.is_integer() else str(result)
                    if op_type == ast.Sub:
                        return f"{expr} = {result}. This means {right} subtracted from {left} gives {r_str}."
                    elif op_type == ast.Add:
                        return f"{expr} = {result}. This means {left} added to {right} gives {r_str}."
                    elif op_type == ast.Mult:
                        return f"{expr} = {result}. This means {left} multiplied by {right} gives {r_str}."
                    else:
                        return f"{expr} = {result}. This means {left} {op_word} {right} gives {r_str}."
        except Exception:
            pass
            
        return f"{expr} = {result}. This is the computed value for the expression."

    def _get_ast_val(self, node: ast.AST) -> str:
        """Helper to get printable values from AST nodes."""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif type(node).__name__ == "Num":
            return str(node.n)
        elif isinstance(node, ast.BinOp):
            return f"({self._get_ast_val(node.left)} {type(node.op).__name__} {self._get_ast_val(node.right)})"
        return "the value"

    def _synthesize_keyword(self, response: SuboperatorResponse) -> str:
        """Formats keyword facts."""
        parts = []
        for fact in response.facts:
            fact_type = fact.get("type")
            if fact_type == "greeting":
                parts.append(fact.get("value", "Welcome to the Colony"))
            elif fact_type == "keyword_match":
                keyword = fact.get("keyword")
                value = fact.get("value")
                parts.append(f"Matched keyword '{keyword}': {value}")
            elif fact_type == "language":
                parts.append(f"Detected language: {fact.get('value')}.")
            elif fact_type == "intent_word":
                parts.append(f"Intent verb detected: {fact.get('value')}.")
            elif fact_type == "number":
                parts.append(f"Number: {fact.get('value')}.")
            elif fact_type == "email":
                parts.append(f"Email: {fact.get('value')}.")
            elif fact_type == "url":
                parts.append(f"URL: {fact.get('value')}.")
            elif fact_type == "date":
                parts.append(f"Date: {fact.get('value')}.")
            elif fact_type == "key_noun":
                parts.append(f"Key noun: {fact.get('value')}.")
        if parts:
            return "\n".join(parts)
        return "Keyword operation succeeded, but no matches were found."

    def _synthesize_code(self, response: SuboperatorResponse) -> str:
        """Formats code analysis facts."""
        parts = []
        for fact in response.facts:
            fact_type = fact.get("type")
            if fact_type == "code_language":
                lang = fact.get("language")
                conf = fact.get("confidence", 1.0)
                parts.append(f"Detected programming language: {lang} (confidence: {conf:.2f}).")
            elif fact_type == "syntax_check":
                valid = fact.get("valid")
                if valid:
                    parts.append("Syntax check: Code is syntactically valid.")
                else:
                    err = fact.get("error", "Unknown error")
                    line = fact.get("line", 1)
                    offset = fact.get("offset", 0)
                    parts.append(f"Syntax check: Code has syntax errors: {err} at line {line}, offset {offset}.")
            elif fact_type == "bug_category":
                cat = fact.get("category")
                desc = fact.get("description")
                line = fact.get("line", 1)
                parts.append(f"Bug analysis: Identified {cat} issue: {desc} (line {line}).")
        if parts:
            return "\n".join(parts)
        return "Code analysis completed."

    def _synthesize_planner(self, response: SuboperatorResponse) -> str:
        """Formats planning facts into sequential step lists."""
        parts = []
        for fact in response.facts:
            fact_type = fact.get("type")
            if fact_type == "plan":
                steps = fact.get("steps", [])
                deps = fact.get("dependencies", {})
                
                steps_str = []
                for idx, step in enumerate(steps, 1):
                    step_deps = deps.get(step, [])
                    if step_deps:
                        deps_str = f" (depends on: {', '.join(step_deps)})"
                    else:
                        deps_str = ""
                    steps_str.append(f"{idx}. {step}{deps_str}")
                
                parts.append("Decomposed Plan:\n" + "\n".join(steps_str))
        if parts:
            return "\n".join(parts)
        return "Plan outline completed."

    def _synthesize_generic(self, response: SuboperatorResponse) -> str:
        """Generic fallback synthesizer for facts."""
        parts = []
        for fact in response.facts:
            parts.append(str(fact))
        if parts:
            return f"Facts from {response.operator}:\n" + "\n".join(parts)
        return f"Operation {response.operator} completed successfully."

    def _generate_debug_block(
        self, 
        verified_responses: List[SuboperatorResponse], 
        final_answer: str,
        verification_result: Optional[Any] = None,
        routed_operators: Optional[List[str]] = None
    ) -> str:
        """Generates standard debug block string."""
        if routed_operators:
            selected_ops = ", ".join(routed_operators)
        else:
            selected_ops = ", ".join(set(r.operator for r in verified_responses))
            
        if not selected_ops:
            selected_ops = "None"

        if verification_result:
            num_verified = len(verification_result.facts)
            num_rejected = len(verification_result.rejected)
        else:
            num_verified = sum(len(r.facts) for r in verified_responses)
            num_rejected = 0
            
        return (
            "--- Debug Output ---\n"
            f"Selected operators: {selected_ops}\n"
            f"Verified facts: {num_verified}\n"
            f"Rejected facts: {num_rejected}\n"
            f"Final answer: {final_answer}"
        )

    def _synthesize_memory(self, response: SuboperatorResponse) -> str:
        """Formats memory facts."""
        parts = []
        for fact in response.facts:
            fact_type = fact.get("type")
            key = fact.get("key", "")
            value = fact.get("value", "")
            key_clean = key.replace("_", " ")
            
            if fact_type == "stored_preference":
                parts.append(f"I have stored your {key_clean} as {value}.")
            elif fact_type == "retrieved_preference":
                parts.append(f"Your {key_clean} is {value}.")
            elif fact_type == "preference_not_found":
                parts.append(f"I could not find a remembered value for your {key_clean}.")
            elif fact_type == "memory_context":
                parts.append(f"Remembered context: {key_clean} is {value}.")
        if parts:
            return "\n".join(parts)
        return "Memory operation completed."

    def _synthesize_tool(self, response: SuboperatorResponse) -> str:
        """Formats tool execution facts."""
        parts = []
        for fact in response.facts:
            fact_type = fact.get("type")
            if fact_type == "tool_call":
                tool = fact.get("tool")
                output = fact.get("output")
                if tool == "file_reader":
                    path = fact.get("path")
                    timestamp = fact.get("timestamp")
                    parts.append(f"Read file '{path}' at {timestamp}. Content:\n{output}")
                elif tool == "web_fetcher":
                    source_url = fact.get("source_url")
                    parts.append(f"Fetched content from URL '{source_url}':\n{output}")
                elif tool == "shell_runner":
                    exit_code = fact.get("exit_code")
                    parts.append(f"Shell command executed with exit code {exit_code}. Output:\n{output}")
                elif tool == "file_deleter":
                    parts.append(output)
                elif tool == "datetime":
                    parts.append(f"Current date and time is {output}.")
                else:
                    parts.append(f"Tool '{tool}' executed successfully. Output: {output}")
        if parts:
            return "\n".join(parts)
        return "Tool execution succeeded."

    def _compress_facts(self, facts: List[Dict[str, Any]]) -> str:
        """
        Compresses verbose JSON facts into a highly optimized, compact textual format
        to reduce token consumption and KV cache footprint in low-resource environments.
        """
        compressed_lines = []
        for fact in facts:
            fact_type = fact.get("type")
            operator = fact.get("operator", "")
            op_str = f"({operator}) " if operator else ""
            
            if fact_type == "calculation":
                expr = fact.get("expression")
                res = fact.get("result")
                compressed_lines.append(f"{op_str}[calc: {expr} = {res}]")
            elif fact_type == "code_language":
                lang = fact.get("language")
                compressed_lines.append(f"{op_str}[code_lang: {lang}]")
            elif fact_type == "syntax_check":
                lang = fact.get("language")
                valid = fact.get("valid", False)
                if valid:
                    compressed_lines.append(f"{op_str}[syntax: {lang} is valid]")
                else:
                    err = fact.get("error", "unknown error")
                    line = fact.get("line", 1)
                    compressed_lines.append(f"{op_str}[syntax: {lang} invalid (error: {err} at line {line})]")
            elif fact_type == "bug_category":
                cat = fact.get("category")
                desc = fact.get("description")
                line = fact.get("line", 1)
                compressed_lines.append(f"{op_str}[bug: {cat} at line {line}: {desc}]")
            elif fact_type == "plan":
                steps = fact.get("steps", [])
                steps_str = ", ".join(steps)
                compressed_lines.append(f"{op_str}[plan: {steps_str}]")
            elif fact_type == "tool_call":
                tool = fact.get("tool")
                tool_input = fact.get("input", "")
                success = fact.get("success", False)
                output = fact.get("output", "")
                # Truncate long tool outputs
                output_snippet = str(output)[:150] + "..." if len(str(output)) > 150 else str(output)
                status = "success" if success else "failed"
                compressed_lines.append(f"{op_str}[tool: {tool}({tool_input}) -> {status}: {output_snippet}]")
            elif fact_type in ("greeting", "keyword_match"):
                kw = fact.get("keyword")
                val = fact.get("value")
                compressed_lines.append(f"{op_str}[keyword: {kw} -> {val}]")
            elif fact_type in ("stored_preference", "retrieved_preference", "memory_context"):
                key = fact.get("key")
                val = fact.get("value")
                compressed_lines.append(f"{op_str}[memory: {key} = {val}]")
            elif fact_type == "preference_not_found":
                key = fact.get("key")
                compressed_lines.append(f"{op_str}[memory: {key} not found]")
            else:
                # Fallback format for any generic facts
                fact_copy = {k: v for k, v in fact.items() if k not in ("type", "operator")}
                fact_str = ", ".join(f"{k}={v}" for k, v in fact_copy.items())
                compressed_lines.append(f"{op_str}[{fact_type or 'fact'}: {fact_str}]")
                
        return "\n".join(compressed_lines)



