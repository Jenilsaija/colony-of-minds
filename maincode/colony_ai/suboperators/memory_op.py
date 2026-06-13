"""
Memory specialist suboperator.
Extracts facts and preferences from prompts to store in or query from long-term SQLite database.
"""

import re
from typing import Optional, List, Dict, Any
from colony.operator import BaseSuboperator
from colony.schemas import SuboperatorResponse
from memory.memory_store import MemoryStore

OPERATOR_INFO = {
    "name": "memory_op",
    "version": "0.1.0",
    "capabilities": ["storage", "retrieval", "history_search"],
    "cost": "low",
    "safe_for_parallel": False
}


class MemoryOperator(BaseSuboperator):
    """
    Suboperator that acts as the memory access client.
    Interacts with the SQLite database to store user preferences/facts and recall them.
    """

    @property
    def name(self) -> str:
        return "memory_op"

    def execute(self, query: str, context: Optional[dict] = None) -> SuboperatorResponse:
        query_clean = query.strip()
        query_lower = query_clean.lower()
        facts = []
        confidence = 0.5
        
        db = MemoryStore()

        # 1. Detect Save preference intent
        # Format: "Remember (that) (my) [key] is [value]"
        save_match = re.search(
            r"\bremember\s+(?:that\s+)?(?:my\s+)?([\w\s_-]+?)\s+(?:is|was|to\s+be)\s+(.+)",
            query_clean,
            re.IGNORECASE
        )
        if save_match:
            raw_key = save_match.group(1).strip()
            val = save_match.group(2).strip().rstrip(".")
            key = raw_key.lower().replace(" ", "_")
            
            # Store in both facts and preferences tables
            db.store_preference(key, val)
            db.store_fact(key, val, source="user")
            
            facts.append({
                "type": "stored_preference",
                "key": key,
                "value": val
            })
            confidence = 1.0

        # 2. Detect Retrieve preference intent
        # Format: "What is my [key]?", "What was my [key]?", "Recall [key]"
        # Avoid matching if we already matched save intent
        retrieve_match = re.search(
            r"\b(?:what|was|were|is|are|recall|retrieve)\s+(?:is|was|are|were|my\s+)?(?:my\s+)?([\w\s_-]+?)(?:\?|$)",
            query_lower,
            re.IGNORECASE
        )
        if retrieve_match and not save_match:
            raw_key = retrieve_match.group(1).strip()
            key = raw_key.lower().replace(" ", "_")
            if key.startswith("my_"):
                key = key[3:]

            # Retrieve from preferences, fallback to facts table
            pref = db.get_preference(key)
            if not pref:
                pref = db.get_fact(key)

            if pref:
                facts.append({
                    "type": "retrieved_preference",
                    "key": key,
                    "value": pref["value"]
                })
                confidence = 1.0
            else:
                # If exact match fails, do a fuzzy/substring search
                search_results = db.search_facts_and_preferences(raw_key)
                if search_results:
                    match = search_results[0]
                    facts.append({
                        "type": "retrieved_preference",
                        "key": match["key"],
                        "value": match["value"]
                    })
                    confidence = 0.90
                else:
                    facts.append({
                        "type": "preference_not_found",
                        "key": key
                    })
                    confidence = 0.80

        # 3. Fallback: Contextual search
        # If no explicit save/retrieve matched, search keywords to yield relevant facts
        if not facts:
            stop_words = {"what", "is", "my", "the", "and", "a", "an", "to", "in", "on", "at", "for", "with"}
            words = [w for w in re.findall(r"\b\w{3,}\b", query_lower) if w not in stop_words]
            
            context_facts = []
            seen_keys = set()
            for word in words:
                matches = db.search_facts_and_preferences(word)
                for m in matches:
                    k = m["key"]
                    if k not in seen_keys:
                        seen_keys.add(k)
                        context_facts.append({
                            "type": "memory_context",
                            "key": k,
                            "value": m["value"]
                        })
            
            if context_facts:
                facts.extend(context_facts[:3])
                confidence = 0.70

        return SuboperatorResponse(
            operator=self.name,
            success=True,
            confidence=confidence if facts else 0.1,
            facts=facts
        )
