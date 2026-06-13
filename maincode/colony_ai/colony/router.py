import re
from typing import List, Dict, Tuple
from colony.schemas import RouterResponse

class Router:
    """
    Decides which specialist suboperators are needed to fulfill a query.
    Implements multi-label routing based on keyword and regex pattern triggers.
    """

    def route(self, query: str) -> RouterResponse:
        """
        Determine which operators are needed to process the query, providing reasoning
        and confidence metrics.
        
        Args:
            query: The user query string.
            
        Returns:
            A RouterResponse contract specifying operators, reason, and confidence.
        """
        query_clean = query.strip()
        query_lower = query_clean.lower()
        
        # Tokenize query to match complete words instead of substrings for keywords
        words = set(re.findall(r"\b\w+\b", query_lower))

        # Operators regex pattern matchers (Level 2)
        math_regex_pattern = r"\b\d+\s*[\+\-\*\/\%\&\|\^\~]\s*\d+\b"
        
        code_regex_patterns = [
            r"\bdef\s+\w+\b",
            r"\bclass\s+\w+\b",
            r"\bimport\s+\w+\b",
            r"\bfrom\s+\w+\s+import\b",
            r"\{\s*.*?\s*\}",  # Curly brace content
            r"\bprint\s*\(",
            r"\bconsole\.log\s*\(",
            r"\bfor\s+\w+\s+in\s+",
        ]
        
        url_regex_pattern = r"https?://[^\s]+|www\.[^\s]+"

        matched_ops: Dict[str, Tuple[float, str]] = {}

        # 1. Math Specialist Trigger Rules
        math_keywords = {"calculate", "compute", "sum", "multiply", "subtract", "divide", "add", "math", "calc"}
        math_word_matches = math_keywords.intersection(words)
        math_regex_match = re.search(math_regex_pattern, query_clean)
        
        if math_word_matches or math_regex_match:
            details = []
            conf = 0.5
            if math_word_matches:
                details.append(f"keyword(s) {sorted(list(math_word_matches))}")
                conf = max(conf, 0.90)
            if math_regex_match:
                details.append(f"arithmetic pattern '{math_regex_match.group()}'")
                conf = max(conf, 0.85)
            # If both keywords and syntax matched, boost confidence
            if math_word_matches and math_regex_match:
                conf = max(conf, 0.95)
            matched_ops["math_op"] = (conf, " + ".join(details))

        # 2. Code Specialist Trigger Rules
        code_keywords = {"code", "bug", "syntax", "function", "python", "javascript", "java", "c++", "programming", "compile", "script"}
        code_word_matches = code_keywords.intersection(words)
        
        code_regex_match = None
        for pat in code_regex_patterns:
            m = re.search(pat, query_clean)
            if m:
                code_regex_match = m.group()
                break
                
        if code_word_matches or code_regex_match:
            details = []
            conf = 0.5
            if code_word_matches:
                details.append(f"keyword(s) {sorted(list(code_word_matches))}")
                conf = max(conf, 0.90)
            if code_regex_match:
                details.append(f"code construct '{code_regex_match}'")
                conf = max(conf, 0.85)
            if code_word_matches and code_regex_match:
                conf = max(conf, 0.95)
            matched_ops["code_op"] = (conf, " + ".join(details))

        # 3. Planner Specialist Trigger Rules
        planner_keywords = {"plan", "steps", "roadmap", "todo", "tasks", "schedule", "outline", "list"}
        planner_word_matches = planner_keywords.intersection(words)
        if planner_word_matches:
            matched_ops["planner_op"] = (0.90, f"keyword(s) {sorted(list(planner_word_matches))}")

        # 4. Memory Specialist Trigger Rules
        memory_keywords = {"remember", "recall", "memory", "preference", "preferences", "forget", "history", "store", "save"}
        memory_word_matches = memory_keywords.intersection(words)
        memory_pattern_match = re.search(r"\bwhat\s+(?:is|was|are|were)\s+my\b", query_lower) or re.search(r"\bremember\b", query_lower)
        
        if memory_word_matches or memory_pattern_match:
            details = []
            conf = 0.5
            if memory_word_matches:
                details.append(f"keyword(s) {sorted(list(memory_word_matches))}")
                conf = max(conf, 0.90)
            if memory_pattern_match:
                details.append("memory prompt pattern")
                conf = max(conf, 0.90)
            matched_ops["memory_op"] = (conf, " + ".join(details))

        # 5. Tool Specialist Trigger Rules
        tool_keywords = {"fetch", "read", "delete", "shell", "run", "datetime", "execute"}
        tool_word_matches = tool_keywords.intersection(words)
        tool_patterns = [
            r"\bread\s+file\b",
            r"\bdelete\s+file\b",
            r"\brun\s+command\b",
            r"\bcurrent\s+time\b",
            r"\bweb_fetcher\b",
            r"\bfile_reader\b",
            r"\bshell_runner\b",
            r"\bfile_deleter\b"
        ]
        tool_pattern_match = None
        for pat in tool_patterns:
            m = re.search(pat, query_lower)
            if m:
                tool_pattern_match = m.group()
                break
                
        if tool_word_matches or tool_pattern_match:
            details = []
            conf = 0.5
            if tool_word_matches:
                details.append(f"keyword(s) {sorted(list(tool_word_matches))}")
                conf = max(conf, 0.90)
            if tool_pattern_match:
                details.append(f"tool pattern '{tool_pattern_match}'")
                conf = max(conf, 0.90)
            matched_ops["tool_op"] = (conf, " + ".join(details))

        # 6. Keyword/General Specialist Trigger Rules
        keyword_keywords = {"summarize", "keywords", "extract", "find", "hello", "hi", "hey", "colony", "mind", "minds", "explain", "explanation", "help", "support", "features", "capabilities", "commands"}
        keyword_word_matches = keyword_keywords.intersection(words)
        url_match = re.search(url_regex_pattern, query_clean)
        
        if keyword_word_matches or url_match:
            details = []
            conf = 0.5
            if keyword_word_matches:
                details.append(f"keyword(s) {sorted(list(keyword_word_matches))}")
                conf = max(conf, 0.90)
            if url_match:
                details.append(f"URL pattern '{url_match.group()}'")
                conf = max(conf, 0.85)
            if keyword_word_matches and url_match:
                conf = max(conf, 0.95)
            matched_ops["keyword_op"] = (conf, " + ".join(details))

        # 5. Synthesize Output Routing Payload
        if matched_ops:
            selected = sorted(list(matched_ops.keys()))
            overall_confidence = max(conf for conf, _ in matched_ops.values())
            reasons = []
            for op in selected:
                _, detail = matched_ops[op]
                reasons.append(f"'{op}' because of {detail}")
            reason = "Matches: " + "; ".join(reasons)
        else:
            # Fallback strategy if no triggers match
            selected = ["keyword_op"]
            overall_confidence = 0.5
            reason = "No matching keyword or structural patterns found. Falling back to default operator."

        return RouterResponse(
            selected_operators=selected,
            reason=reason,
            confidence=overall_confidence
        )
