#!/usr/bin/env python3
"""
Quickstart Guide: Colony of Minds AI

This script demonstrates how to run the Colony of Minds pipeline programmatically, 
and how to define and register a custom developer suboperator.
"""

import sys
import os
from pathlib import Path

# Add core project to path
sys.path.append(str(Path(__file__).resolve().parent / "colony_ai"))

# Core imports
from colony_ai.run_colony import run_pipeline, register_suboperator, get_operator
from colony_ai.colony.operator import BaseSuboperator
from colony_ai.colony.schemas import SuboperatorResponse
from colony_ai.colony.router import Router

# =====================================================================
# 1. DEFINE A CUSTOM SUBOPERATOR
# =====================================================================
class EchoOperator(BaseSuboperator):
    """
    A simple custom developer suboperator that repeats facts and matches hello.
    """
    @property
    def name(self) -> str:
        return "echo_op"

    def execute(self, query: str, context: dict = None) -> SuboperatorResponse:
        # Business logic goes here
        # Return a standardized SuboperatorResponse
        facts = [{
            "type": "echo_response",
            "message": f"Echo: {query}",
            "char_count": len(query)
        }]
        return SuboperatorResponse(
            operator=self.name,
            success=True,
            confidence=0.99,
            facts=facts
        )

# =====================================================================
# 2. RUN DEMO
# =====================================================================
def main():
    print("=== Colony of Minds Programmatic Quickstart ===")
    
    # Register the custom suboperator
    echo_instance = EchoOperator()
    register_suboperator("echo_op", echo_instance)
    print(f"[*] Custom suboperator '{echo_instance.name}' registered successfully.")

    # 1. Test basic run pipeline (Math verification)
    prompt = "calculate 45 * 123"
    print(f"\nPrompting: '{prompt}'")
    answer = run_pipeline(prompt, verbose=True)
    print("\nFinal Response:")
    print(answer)

    # 2. Programmatically execute our custom suboperator
    print(f"\n[*] Direct execution call to our '{echo_instance.name}':")
    resp = get_operator("echo_op").execute("Welcome to Colony of Minds")
    print(f"Success: {resp.success}")
    print(f"Confidence: {resp.confidence}")
    print(f"Facts: {resp.facts}")

    print("\n==============================================")
    print("Quickstart run finished. Framework is operating correctly!")

if __name__ == "__main__":
    main()
