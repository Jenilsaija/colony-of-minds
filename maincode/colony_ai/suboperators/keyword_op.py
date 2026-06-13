"""
Keyword specialist suboperator.
Performs deterministic keyword, entity, and pattern extraction and returns structured matching facts.
"""

import re
from typing import Optional, List, Dict, Any
from colony.operator import BaseSuboperator
from colony.schemas import SuboperatorResponse

OPERATOR_INFO = {
    "name": "keyword_op",
    "version": "0.1.0",
    "capabilities": ["extraction", "metadata"],
    "cost": "low",
    "safe_for_parallel": True
}

class KeywordOperator(BaseSuboperator):
    """
    Keyword suboperator looks for specific structural patterns and phrases in a user's prompt
    and yields matching metadata or pre-defined system facts.
    """

    @property
    def name(self) -> str:
        return "keyword_op"

    def execute(self, query: str, context: Optional[dict] = None) -> SuboperatorResponse:
        """
        Scan query for keywords, numbers, URLs, emails, dates, languages, and action verbs/intents.
        """
        query_clean = query.strip()
        query_lower = query_clean.lower()
        
        # Tokenize query to match complete words instead of substrings
        words = set(re.findall(r"\b\w+\b", query_lower))
        facts = []
        confidence = 0.5

        # 1. Extract Emails
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        emails = re.findall(email_pattern, query_clean)
        for email in emails:
            facts.append({
                "type": "email",
                "value": email
            })
            confidence = max(confidence, 0.95)

        # 2. Extract URLs
        url_pattern = r"https?://[^\s]+|www\.[^\s]+"
        urls = re.findall(url_pattern, query_clean)
        for url in urls:
            # Clean up trailing punctuation
            clean_url = url.rstrip(".,;!?()[]{}")
            facts.append({
                "type": "url",
                "value": clean_url
            })
            confidence = max(confidence, 0.95)

        # Remove URLs and emails temporarily from text to avoid false positive numbers
        temp_text = query_clean
        for email in emails:
            temp_text = temp_text.replace(email, "")
        for url in urls:
            temp_text = temp_text.replace(url, "")

        # 3. Extract Dates
        # Matches patterns like YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, and month names
        date_patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b(?:\d{1,2}\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b"
        ]
        found_dates = []
        for pat in date_patterns:
            matches = re.findall(pat, temp_text, re.IGNORECASE)
            for m in matches:
                # Avoid duplicate dates
                if m not in found_dates:
                    found_dates.append(m)
                    facts.append({
                        "type": "date",
                        "value": m
                    })
                    confidence = max(confidence, 0.95)
                    # Remove from temp_text to avoid matching as plain numbers
                    temp_text = temp_text.replace(m, "")

        # 4. Extract Numbers
        # Matches integers and decimal numbers. Avoids matching digits embedded in words.
        number_matches = re.findall(r"\b\d+(?:\.\d+)?\b", temp_text)
        for num_str in number_matches:
            # Check if it was part of an extracted date or email
            try:
                if "." in num_str:
                    val = float(num_str)
                else:
                    val = int(num_str)
                facts.append({
                    "type": "number",
                    "value": val
                })
                confidence = max(confidence, 0.90)
            except ValueError:
                pass

        # 5. Languages detection
        known_languages = {
            "python", "javascript", "js", "typescript", "ts", "java", "cpp", "c++", 
            "c#", "ruby", "go", "golang", "rust", "php", "html", "css", "sql", 
            "bash", "shell", "english", "spanish", "french", "german", "chinese", "japanese"
        }
        for lang in known_languages:
            if lang in words:
                facts.append({
                    "type": "language",
                    "value": lang
                })
                confidence = max(confidence, 0.90)

        # 6. Intent words / Action verbs
        intent_verbs = {
            "calculate", "compute", "solve", "run", "compile", "execute", "check", 
            "verify", "plan", "roadmap", "todo", "list", "explain", "summarize", 
            "extract", "find", "parse", "detect", "identify"
        }
        for verb in intent_verbs:
            if verb in words:
                facts.append({
                    "type": "intent_word",
                    "value": verb
                })
                confidence = max(confidence, 0.90)

        # 7. Greetings
        if any(greet in words for greet in ["hello", "hi", "hey", "welcome"]):
            facts.append({
                "type": "greeting",
                "keyword": "hello",
                "value": "Welcome to the Colony"
            })
            confidence = 1.0

        # 8. Framework keywords
        if "colony" in words:
            facts.append({
                "type": "keyword_match",
                "keyword": "colony",
                "value": "An AI framework utilizing specialized composition rather than single large models."
            })
            confidence = max(confidence, 0.95)

        if "mind" in words or "minds" in words:
            facts.append({
                "type": "keyword_match",
                "keyword": "minds",
                "value": "The specialized suboperators that compose the collective intelligence."
            })
            confidence = max(confidence, 0.90)

        if "atma" in words:
            facts.append({
                "type": "keyword_match",
                "keyword": "atma",
                "value": "The voice synthesis layer of the Colony of Minds that reads verified facts."
            })
            confidence = max(confidence, 0.90)

        # Help and capabilities keywords
        help_keywords = {"help", "capabilities", "features", "commands", "support"}
        matched_help = help_keywords.intersection(words)
        if matched_help:
            facts.append({
                "type": "keyword_match",
                "keyword": "help",
                "value": "I am the Colony of Minds assistant. I can help you with: 1. Mathematics & calculation (math_op), 2. Code syntax & bug analysis (code_op), 3. Task planning (planner_op), 4. Persisting memory & preferences (memory_op), 5. Executing system tools (tool_op), and 6. Extracting key entities (keyword_op)."
            })
            confidence = max(confidence, 0.95)

        # 9. Key Nouns (e.g. GST, invoice, bug, structure, syntax, pipeline)
        key_nouns = {"gst", "invoice", "bug", "structure", "syntax", "pipeline"}
        for noun in key_nouns:
            if noun in words:
                facts.append({
                    "type": "key_noun",
                    "value": noun
                })
                confidence = max(confidence, 0.85)

        return SuboperatorResponse(
            operator=self.name,
            success=True,
            confidence=confidence if facts else 0.1,
            facts=facts
        )
