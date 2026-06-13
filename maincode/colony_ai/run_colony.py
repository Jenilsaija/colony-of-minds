#!/usr/bin/env python3
"""
CLI entry point for the Colony of Minds AI framework.
Coordinates query routing, suboperator execution, safety verification, response synthesis, and memory persistence.
"""

import sys
import argparse
import json
import time
import datetime
from typing import List, Optional

# Ensure package directories are in sys.path if run directly
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from colony.router import Router
from colony.verifier import Verifier
from colony.atma import Atma
from memory.memory_store import MemoryStore
from colony.schemas import SuboperatorResponse

_LAZY_OPERATORS = {}
_REGISTERED_OPERATORS = {}

def register_suboperator(name: str, operator_instance):
    """Programmatically register a custom suboperator."""
    _REGISTERED_OPERATORS[name] = operator_instance

def discover_plugins():
    """Dynamically discover and register custom suboperators in plugins directory."""
    import importlib.util
    import inspect
    from colony.operator import BaseSuboperator
    
    plugins_dir = Path(__file__).resolve().parent / "plugins" / "suboperators"
    if not plugins_dir.exists():
        return
        
    for py_file in plugins_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        module_name = f"colony_ai.plugins.suboperators.{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for item_name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseSuboperator) and 
                        obj is not BaseSuboperator):
                        instance = obj()
                        register_suboperator(instance.name, instance)
        except Exception:
            pass

# Run plugin discovery once on module load
discover_plugins()

def get_operator(name: str):
    """Lazy-load and cache suboperators to optimize memory usage."""
    if name not in _LAZY_OPERATORS:
        if name in _REGISTERED_OPERATORS:
            _LAZY_OPERATORS[name] = _REGISTERED_OPERATORS[name]
        elif name == "keyword_op":
            from suboperators.keyword_op import KeywordOperator
            _LAZY_OPERATORS[name] = KeywordOperator()
        elif name == "math_op":
            from suboperators.math_op import MathOperator
            _LAZY_OPERATORS[name] = MathOperator()
        elif name == "code_op":
            from suboperators.code_op import CodeOperator
            _LAZY_OPERATORS[name] = CodeOperator()
        elif name == "planner_op":
            from suboperators.planner_op import PlannerOperator
            _LAZY_OPERATORS[name] = PlannerOperator()
        elif name == "memory_op":
            from suboperators.memory_op import MemoryOperator
            _LAZY_OPERATORS[name] = MemoryOperator()
        elif name == "tool_op":
            from suboperators.tool_op import ToolOperator
            _LAZY_OPERATORS[name] = ToolOperator()
        else:
            raise ValueError(f"Unknown operator name: {name}")
    return _LAZY_OPERATORS[name]

class LazyOperatorRegistry(dict):
    def get(self, key, default=None):
        try:
            return get_operator(key)
        except ValueError:
            return default

    def __getitem__(self, key):
        return get_operator(key)

OPERATOR_REGISTRY = LazyOperatorRegistry()

def get_process_memory_mb() -> float:
    """Returns process Resident Set Size (RSS) in MB. Returns 0.0 if psutil is not available."""
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0

def run_pipeline(
    query: str, 
    verbose: bool = False, 
    model_name: Optional[str] = None, 
    ollama_path: Optional[str] = None,
    ollama_api_url: Optional[str] = None
) -> str:
    """
    Executes the complete colony pipeline for a given query.
    """
    # 1. Initialize core assets
    router = Router()
    verifier = Verifier()
    atma = Atma()
    memory = MemoryStore()

    if verbose:
        print(f"[*] Input Query: '{query}'")

    # 2. Router decides which suboperators should execute
    router_response = router.route(query)
    selected_ops = router_response.selected_operators
    if verbose:
        print("[*] Router Output:")
        print(json.dumps(router_response.to_dict(), indent=2))

    # 3. Execute specialist suboperators
    context = {"verbose": verbose}  # Enriched with execution context
    responses: List[SuboperatorResponse] = []
    execution_times = {}

    # Helper to execute operator and measure duration
    def run_op_with_metrics(op_name):
        op_instance = OPERATOR_REGISTRY.get(op_name)
        if not op_instance:
            return SuboperatorResponse.create_error(op_name, f"Operator '{op_name}' not found in registry."), 0
        
        t0 = time.time()
        try:
            if verbose:
                print(f"[*] Executing suboperator: {op_name}")
            resp = op_instance.execute(query, context)
            dur = int((time.time() - t0) * 1000)
            return resp, dur
        except Exception as e:
            dur = int((time.time() - t0) * 1000)
            return SuboperatorResponse.create_error(op_name, f"Exception occurred during execution: {e}"), dur

    if len(selected_ops) == 1:
        # Sequential execution for single operator (saves thread overhead)
        op_name = selected_ops[0]
        resp, dur = run_op_with_metrics(op_name)
        responses.append(resp)
        execution_times[op_name] = dur
    elif len(selected_ops) > 1:
        # Parallel execution using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed
        # Limit max_workers to 2 as per the target environment hardware spec
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(run_op_with_metrics, op_name): op_name
                for op_name in selected_ops
            }
            for future in as_completed(futures):
                op_name = futures[future]
                try:
                    resp, dur = future.result()
                    responses.append(resp)
                    execution_times[op_name] = dur
                except Exception as e:
                    responses.append(SuboperatorResponse.create_error(op_name, f"Thread error: {e}"))
                    execution_times[op_name] = 0

    if verbose:
        print("[*] Raw Suboperator Outputs:")
        for r in responses:
            print(json.dumps(r.to_dict(), indent=2))

    # 4. Verify outputs
    verification_result = verifier.verify_all(responses, query, selected_ops)
    
    if verbose:
        print("[*] Verifier Output:")
        print(json.dumps(verification_result.to_dict(), indent=2))

    # Reconstruct verified SuboperatorResponse list for Atma speak (maintaining compatibility)
    verified_responses: List[SuboperatorResponse] = []
    op_responses = {}
    for fact in verification_result.facts:
        op = fact.get("operator", "unknown")
        # Remove internal operator tracking key to keep facts clean
        fact_clean = {k: v for k, v in fact.items() if k != "operator"}
        op_responses.setdefault(op, []).append(fact_clean)

    for op, facts in op_responses.items():
        orig_resp = next((r for r in responses if r.operator == op), None)
        conf = orig_resp.confidence if orig_resp else 1.0
        verified_responses.append(SuboperatorResponse(
            operator=op,
            success=True,
            confidence=conf,
            facts=facts
        ))

    # 5. Synthesize final answer via Atma
    atma_context = {}
    final_output = atma.speak(
        query=query,
        verified_responses=verified_responses,
        verbose=verbose,
        verification_result=verification_result,
        routed_operators=selected_ops,
        model_name=model_name,
        ollama_path=ollama_path,
        context=atma_context,
        ollama_api_url=ollama_api_url
    )
    
    # 6. Store interaction details in memory
    try:
        memory.log_interaction(
            query=query,
            response=final_output,
            routed_operators=selected_ops,
            verified=verification_result.verified,
            verified_facts=verification_result.facts
        )
    except Exception as e:
        if verbose:
            print(f"[!] Error writing to memory store: {e}")

    # 7. Collect and log execution and memory metrics
    mem_after = get_process_memory_mb()
    metrics_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt_length": len(query),
        "selected_operators": selected_ops,
        "execution_times_ms": execution_times,
        "memory_usage_mb": mem_after,
        "atma_mode": atma_context.get("atma_mode", "template")
    }
    
    workspace_root = Path(__file__).resolve().parent.parent
    metrics_file_path = workspace_root / "colony_run_metrics.jsonl"
    try:
        with open(metrics_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics_data) + "\n")
    except Exception as e:
        if verbose:
            print(f"[!] Error writing to metrics log: {e}")

    if verbose:
        print("[*] Observability Metrics:")
        print(json.dumps(metrics_data, indent=2))

    return final_output


def main():
    parser = argparse.ArgumentParser(
        description="Colony of Minds AI - Low-resource composition-based agent framework (Phase 2)"
    )
    parser.add_argument(
        "query", 
        type=str, 
        nargs="?", 
        default=None, 
        help="The prompt/query to process."
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Show internal routing and intermediate JSON payloads."
    )
    parser.add_argument(
        "--history", "-log", 
        action="store_true", 
        help="Print the interaction logs stored in SQLite memory store and exit."
    )
    parser.add_argument(
        "--model-name", 
        type=str, 
        default=None, 
        help="Name of the Ollama model to run (e.g. qwen2.5:0.5b)."
    )
    parser.add_argument(
        "--ollama-path", 
        type=str, 
        default=None, 
        help="Path to the ollama binary (e.g. ollama)."
    )
    parser.add_argument(
        "--ollama-api-url", 
        type=str, 
        default=None, 
        help="Ollama HTTP API URL (e.g. http://localhost:11434)."
    )

    args = parser.parse_args()

    # If history flag is set, print SQLite database logs
    if args.history:
        memory = MemoryStore()
        history = memory.get_history(15)
        if not history:
            print("No interaction history found.")
        else:
            print("=== Colony Memory Interaction Logs ===")
            for idx, item in enumerate(history, 1):
                print(f"\n{idx}. [{item['timestamp']}]")
                print(f"   Query: {item['query']}")
                print(f"   Response: {item['response']}")
                print(f"   Routed: {item['routed_operators']}")
                print(f"   Verified: {item['verified']}")
        sys.exit(0)

    # Check for empty query
    if not args.query:
        parser.print_help()
        sys.exit(1)

    # Execute and output response
    answer = run_pipeline(
        args.query, 
        verbose=args.verbose,
        model_name=args.model_name,
        ollama_path=args.ollama_path,
        ollama_api_url=args.ollama_api_url
    )
    print(answer)

if __name__ == "__main__":
    main()
