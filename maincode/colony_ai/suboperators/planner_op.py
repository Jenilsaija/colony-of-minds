"""
Planner specialist suboperator.
Decomposes complex requests into steps, constructing structured plans and estimated task lists.
"""

import re
from typing import Optional, List, Dict, Any
from colony.operator import BaseSuboperator
from colony.schemas import SuboperatorResponse

OPERATOR_INFO = {
    "name": "planner_op",
    "version": "0.1.0",
    "capabilities": ["decomposition", "task_listing", "dependency_estimation"],
    "cost": "low",
    "safe_for_parallel": True
}

class PlannerOperator(BaseSuboperator):
    """
    Planner suboperator analyzes complex multi-part requests and splits them
    into logical execution phases/steps.
    """

    @property
    def name(self) -> str:
        return "planner_op"

    def execute(self, query: str, context: Optional[dict] = None) -> SuboperatorResponse:
        """
        Extract steps from the query and format them into a structured execution plan.
        """
        clean_query = query.strip()
        
        # Strip common instruction prefixes
        prefixes = [
            r"^plan\s+(?:for|to)\s*",
            r"^plan\s+",
            r"^roadmap\s+(?:for|to|of)?\s*",
            r"^steps\s+(?:for|to|of)?\s*",
            r"^todo\s+(?:list\s+for)?\s*",
            r"^outline\s+(?:of|for)?\s*",
            r"^create\s+(?:a\s+)?plan\s+(?:to|for)?\s*",
            r"^give\s+(?:me\s+)?(?:the\s+)?steps\s+(?:to|for)?\s*"
        ]
        for pref in prefixes:
            match = re.match(pref, clean_query, re.IGNORECASE)
            if match:
                clean_query = clean_query[match.end():]
                break

        steps = self._split_into_steps(clean_query)
        if not steps:
            return SuboperatorResponse(
                operator=self.name,
                success=False,
                confidence=0.0,
                errors=["No distinct plan steps could be decomposed from query."]
            )

        # Estimate dependencies: step i depends on step i-1 sequentially
        dependencies = {}
        for idx in range(1, len(steps)):
            dependencies[steps[idx]] = [steps[idx - 1]]

        facts = [{
            "type": "plan",
            "steps": steps,
            "dependencies": dependencies
        }]

        return SuboperatorResponse(
            operator=self.name,
            success=True,
            confidence=0.90 if len(steps) > 1 else 0.5,
            facts=facts
        )

    def _split_into_steps(self, text: str) -> List[str]:
        """
        Decomposes request text into distinct step strings using rule-based parsing.
        """
        # Normalize delimiters by converting "then", "and then", "followed by" to semicolons
        normalized = text
        
        # Replace transition phrases with semicolons
        transitions = [
            r"\band\s+then\b",
            r"\band\s+after\s+that\b",
            r"\bfollowed\s+by\b",
            r"\bsubsequently\b",
            r"\bthen\b"
        ]
        for trans in transitions:
            normalized = re.sub(trans, ";", normalized, flags=re.IGNORECASE)

        # Split by semicolons
        parts = [p.strip() for p in normalized.split(";") if p.strip()]
        
        # If we only have one part, check for "and" splits separating action verb phrases
        if len(parts) == 1:
            # Look for "and" followed by an action verb, e.g. "and write", "and compile", "and add"
            action_verbs = r"\b(?:write|add|compile|run|explain|verify|test|check|create|build|implement|make)\b"
            pattern = r"\s+and\s+(?=" + action_verbs + ")"
            split_parts = re.split(pattern, parts[0], flags=re.IGNORECASE)
            if len(split_parts) > 1:
                parts = [p.strip() for p in split_parts if p.strip()]

        # Clean individual steps
        final_steps = []
        for part in parts:
            # Remove leading punctuation or conjunctions
            cleaned = re.sub(r"^[,\.\s;]+", "", part)
            cleaned = re.sub(r"^(?:and|to|then|after|first|second|third)\s+", "", cleaned, flags=re.IGNORECASE)
            # Remove trailing punctuation
            cleaned = cleaned.rstrip(",.;!? ")
            
            if cleaned:
                # Capitalize first letter
                cleaned = cleaned[0].upper() + cleaned[1:]
                # Avoid inserting short conversational garbage
                if len(cleaned) > 2:
                    final_steps.append(cleaned)

        return final_steps
