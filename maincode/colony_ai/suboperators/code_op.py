"""
Code specialist suboperator.
Detects programming languages, checks syntax, and identifies code issues safely using static analysis.
"""

import ast
import re
from typing import Optional, Dict, Any, List, Tuple
from colony.operator import BaseSuboperator
from colony.schemas import SuboperatorResponse

OPERATOR_INFO = {
    "name": "code_op",
    "version": "0.1.0",
    "capabilities": ["language_detection", "syntax_check", "bug_analysis"],
    "cost": "medium",
    "safe_for_parallel": True
}

class CodeOperator(BaseSuboperator):
    """
    Code suboperator analyzes programming code snippets for language detection,
    syntax validity, and common bug patterns.
    """

    @property
    def name(self) -> str:
        return "code_op"

    def execute(self, query: str, context: Optional[dict] = None) -> SuboperatorResponse:
        """
        Analyze code snippet in the query. Detect language, compile safely if Python, and report findings.
        """
        code_content, language_hint = self._extract_code(query)
        if not code_content:
            return SuboperatorResponse(
                operator=self.name,
                success=False,
                confidence=0.0,
                errors=["No code snippet or programming construct could be extracted from query."]
            )

        facts = []
        confidence = 0.5

        # 1. Detect language
        detected_lang, lang_confidence = self._detect_language(code_content, language_hint)
        facts.append({
            "type": "code_language",
            "language": detected_lang,
            "confidence": lang_confidence
        })
        confidence = max(confidence, lang_confidence)

        # 2. Syntax check (Python is supported via ast.parse)
        if detected_lang == "python":
            is_valid, syntax_details = self._check_python_syntax(code_content)
            facts.append(syntax_details)
            if not is_valid:
                confidence = max(confidence, 0.95)  # High confidence in syntax errors found
            else:
                confidence = max(confidence, 0.90)  # High confidence in syntactically correct python
        else:
            # For non-python languages, perform basic brace-matching syntax checks
            is_valid, syntax_details = self._check_generic_braces(code_content, detected_lang)
            facts.append(syntax_details)
            if not is_valid:
                confidence = max(confidence, 0.80)

        # 3. Identify bug category (if syntax error is found)
        # We also scan for other common bug heuristics
        bug_facts = self._analyze_bug_heuristics(code_content, detected_lang, facts)
        facts.extend(bug_facts)

        return SuboperatorResponse(
            operator=self.name,
            success=True,
            confidence=confidence,
            facts=facts
        )

    def _extract_code(self, query: str) -> Tuple[str, str]:
        """
        Extract code block contents and language hint from the query.
        Returns a tuple of (code_content, language_hint).
        """
        # Search for markdown code blocks: ```lang ... ```
        block_match = re.search(r"```([a-zA-Z0-9+#-]+)?\n(.*?)```", query, re.DOTALL)
        if block_match:
            lang_hint = block_match.group(1) or ""
            code_content = block_match.group(2)
            return code_content.strip(), lang_hint.strip().lower()

        # Search for single backtick blocks: `code`
        inline_match = re.search(r"`([^`]+)`", query)
        if inline_match:
            return inline_match.group(1).strip(), ""

        # Fallback: check if the query contains command prefixes to remove
        clean_query = query.strip()
        prefixes = [
            r"^check\s+(?:the\s+)?syntax\s+(?:for|of)\s*:\s*",
            r"^check\s+(?:the\s+)?syntax\s+(?:for|of)\s*",
            r"^syntax\s+check\s*:\s*",
            r"^syntax\s+check\s*",
            r"^code\s*:\s*"
        ]
        for pref in prefixes:
            match = re.match(pref, clean_query, re.IGNORECASE)
            if match:
                clean_query = clean_query[match.end():]
                break

        # If it still contains programming constructs, we treat the remaining query as code
        code_indicators = [
            r"\bdef\s+\w+", r"\bclass\s+\w+", r"\bimport\s+\w+", r"\bconsole\.log\b",
            r"\bpublic\s+class\s+\w+", r"#include\s+<", r"<!DOCTYPE html>", r"SELECT\s+.*?\s+FROM\b"
        ]
        if any(re.search(ind, clean_query, re.IGNORECASE) for ind in code_indicators):
            return clean_query.strip(), ""

        return "", ""

    def _detect_language(self, code: str, hint: str) -> Tuple[str, float]:
        """
        Identify the programming language from hints and content signatures.
        """
        # Map common extensions/aliases
        hint_map = {
            "py": "python",
            "python": "python",
            "js": "javascript",
            "javascript": "javascript",
            "ts": "typescript",
            "typescript": "typescript",
            "java": "java",
            "cpp": "cpp",
            "c++": "cpp",
            "c": "c",
            "html": "html",
            "sql": "sql",
            "sh": "bash",
            "bash": "bash"
        }
        if hint in hint_map:
            return hint_map[hint], 0.95

        # Heuristic count signatures
        scores = {
            "python": 0,
            "javascript": 0,
            "html": 0,
            "sql": 0,
            "cpp": 0,
            "java": 0
        }

        # Python signatures
        if re.search(r"\bdef\s+\w+\b", code): scores["python"] += 3
        if re.search(r"\bimport\s+(?:os|sys|math|json|ast)\b", code): scores["python"] += 3
        if re.search(r"\belif\s+.*?:", code): scores["python"] += 3
        if re.search(r"\bprint\s*\(", code): scores["python"] += 1
        if "#" in code and not re.search(r"#include|#[0-9a-fA-F]", code): scores["python"] += 1

        # JS/TS signatures
        if "console.log" in code: scores["javascript"] += 4
        if re.search(r"\b(?:const|let|var)\s+\w+", code): scores["javascript"] += 3
        if re.search(r"\bfunction\s+\w+\b", code): scores["javascript"] += 3
        if "=>" in code: scores["javascript"] += 2

        # HTML signatures
        if "</html>" in code.lower() or "<!doctype html>" in code.lower(): scores["html"] += 5
        if re.search(r"<\/?[a-z][a-z0-9]*\b", code, re.IGNORECASE): scores["html"] += 2

        # SQL signatures
        if re.search(r"\bselect\s+.*?\s+from\b", code, re.IGNORECASE): scores["sql"] += 4
        if re.search(r"\binsert\s+into\b", code, re.IGNORECASE): scores["sql"] += 3
        if re.search(r"\bcreate\s+table\b", code, re.IGNORECASE): scores["sql"] += 3

        # C++ signatures
        if "#include" in code: scores["cpp"] += 4
        if "std::" in code: scores["cpp"] += 3
        if "using namespace std" in code: scores["cpp"] += 4

        # Java signatures
        if re.search(r"\bpublic\s+static\s+void\s+main\b", code): scores["java"] += 5
        if "System.out.print" in code: scores["java"] += 4

        max_lang = max(scores, key=scores.get)
        if scores[max_lang] > 0:
            # Set confidence proportional to match strength
            confidence = min(0.5 + (scores[max_lang] * 0.1), 0.90)
            return max_lang, confidence

        # Default fallback
        return "python", 0.3

    def _check_python_syntax(self, code: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate Python syntax using ast.parse (completely safe static compilation).
        """
        try:
            ast.parse(code)
            return True, {
                "type": "syntax_check",
                "language": "python",
                "valid": True
            }
        except SyntaxError as se:
            return False, {
                "type": "syntax_check",
                "language": "python",
                "valid": False,
                "error": f"SyntaxError: {se.msg}",
                "line": se.lineno or 1,
                "offset": se.offset or 0,
                "text": (se.text or "").strip()
            }

    def _check_generic_braces(self, code: str, language: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check for mismatched brackets/parentheses in languages other than Python.
        """
        stack = []
        mapping = {")": "(", "}": "{", "]": "["}
        lines = code.splitlines()

        for line_idx, line in enumerate(lines, 1):
            for char_idx, char in enumerate(line, 1):
                if char in mapping.values():
                    stack.append((char, line_idx, char_idx))
                elif char in mapping.keys():
                    if not stack:
                        return False, {
                            "type": "syntax_check",
                            "language": language,
                            "valid": False,
                            "error": f"Mismatched closing bracket '{char}'",
                            "line": line_idx,
                            "offset": char_idx,
                            "text": line.strip()
                        }
                    top_char, top_line, top_offset = stack.pop()
                    if top_char != mapping[char]:
                        return False, {
                            "type": "syntax_check",
                            "language": language,
                            "valid": False,
                            "error": f"Mismatched brackets: '{char}' closed '{top_char}' from line {top_line}",
                            "line": line_idx,
                            "offset": char_idx,
                            "text": line.strip()
                        }
        if stack:
            top_char, top_line, top_offset = stack.pop()
            return False, {
                "type": "syntax_check",
                "language": language,
                "valid": False,
                "error": f"Unmatched open bracket '{top_char}'",
                "line": top_line,
                "offset": top_offset,
                "text": lines[top_line - 1].strip()
            }

        return True, {
            "type": "syntax_check",
            "language": language,
            "valid": True
        }

    def _analyze_bug_heuristics(self, code: str, language: str, syntax_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze code patterns to categorize likely bugs.
        """
        bug_facts = []

        # Check for syntax errors first
        syntax_check_fact = next((f for f in syntax_facts if f.get("type") == "syntax_check"), None)
        if syntax_check_fact and not syntax_check_fact.get("valid"):
            err_msg = syntax_check_fact.get("error", "").lower()
            err_line = syntax_check_fact.get("line", 1)

            # Categorize the syntax error
            if "indent" in err_msg or "tab" in err_msg:
                bug_facts.append({
                    "type": "bug_category",
                    "category": "indentation",
                    "description": "Code has invalid spaces/tabs alignment or expected blocks.",
                    "line": err_line
                })
            elif "never closed" in err_msg or "unmatched" in err_msg or "mismatched" in err_msg:
                bug_facts.append({
                    "type": "bug_category",
                    "category": "mismatched_brackets",
                    "description": "Braces, brackets, or parentheses are mismatched or not closed properly.",
                    "line": err_line
                })
            elif language == "python":
                # Check for common missing colon signature on structures
                lines = code.splitlines()
                if 0 < err_line <= len(lines):
                    line_content = lines[err_line - 1].strip()
                    structs = ["def ", "class ", "if ", "elif ", "else", "for ", "while ", "try", "except"]
                    if any(line_content.startswith(s) for s in structs) or line_content in structs:
                        if not line_content.endswith(":"):
                            bug_facts.append({
                                "type": "bug_category",
                                "category": "missing_colon",
                                "description": "Block header (def/class/if/for/etc.) is missing its trailing colon.",
                                "line": err_line
                            })
                            return bug_facts

                bug_facts.append({
                    "type": "bug_category",
                    "category": "syntax_error",
                    "description": "Invalid Python syntax construct.",
                    "line": err_line
                })

        # Heuristic check: assignment instead of equality check in conditions (e.g. if x = 5)
        # Only check if syntax is valid or if it's a non-python language
        if language in ["javascript", "cpp", "java"]:
            assign_match = re.search(r"\bif\s*\([^=]*=[^=]*\)", code)
            if assign_match:
                # Find line number
                pre_match = code[:assign_match.start()]
                line_no = len(pre_match.splitlines()) + 1
                bug_facts.append({
                    "type": "bug_category",
                    "category": "assignment_in_condition",
                    "description": "Single equals '=' found in condition check instead of '==' or '===' comparison.",
                    "line": line_no
                })

        return bug_facts
