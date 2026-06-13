import os
import sys
import time
import json
from pathlib import Path

# Add project directories to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from run_colony import run_pipeline, get_process_memory_mb

# 20 Queries representing diverse intents
QUERIES = [
    "hello colony",
    "calculate 45 * 123",
    "Explain 18% GST on 25000",
    "Remember my project name is OpenPrompt.",
    "What is my project name?",
    "Plan the steps to develop a new web app",
    "current time",
    "calculate 1024 / 4",
    "what is my project name?",
    "read file colony_ai/colony/config.py",
    "hello hi minds",
    "calculate (100 - 20) * 5",
    "Remember my favorite color is dark blue.",
    "What is my favorite color?",
    "Plan a vacation roadmap to Japan",
    "calculate 99 * 99",
    "current time",
    "what was my favorite color?",
    "hello hi colony",
    "Calculate 123 + 456 using tool."
]

def main():
    print("=== Colony of Minds Stress Test (20 requests) ===")
    print(f"Initial Process Memory: {get_process_memory_mb():.2f} MB")
    print("--------------------------------------------------")

    latencies = []
    mem_usages = []
    failures = 0

    # We bypass interactive prompts in tool calls for tests
    context_override = {"bypass_confirmation": True}

    # Patch BaseTool._get_confirmation to return True during stress test if needed,
    # or rely on bypass_confirmation context. Our run_pipeline context handles it
    # if passed. Wait, we can pass it through a global config or mock it.
    # To be safe, let's patch BaseTool._get_confirmation dynamically:
    try:
        from colony.tools import BaseTool
        # Save original
        orig_confirm = BaseTool._get_confirmation
        BaseTool._get_confirmation = lambda self, tool_input, context=None: True
    except ImportError:
        pass

    for idx, query in enumerate(QUERIES, 1):
        t0 = time.time()
        success = True
        error_msg = ""
        try:
            # Execute pipeline
            output = run_pipeline(query, verbose=False)
            if not output:
                success = False
                error_msg = "Empty output response"
        except Exception as e:
            success = False
            error_msg = str(e)

        dur = (time.time() - t0) * 1000  # ms
        mem = get_process_memory_mb()

        latencies.append(dur)
        mem_usages.append(mem)

        if not success:
            failures += 1
            print(f"Request {idx:02d}: FAIL | Query: '{query}' | Error: {error_msg}")
        else:
            print(f"Request {idx:02d}: OK   | Latency: {dur:5.1f} ms | Memory: {mem:5.2f} MB | Query: '{query}'")

    # Restore confirmation prompt if patched
    try:
        BaseTool._get_confirmation = orig_confirm
    except Exception:
        pass

    avg_latency = sum(latencies) / len(latencies)
    max_mem = max(mem_usages)
    failure_rate = (failures / len(QUERIES)) * 100

    print("--------------------------------------------------")
    print("=== Performance & Low-RAM Engineering Results ===")
    print(f"Total Requests  : {len(QUERIES)}")
    print(f"Failure Rate    : {failure_rate:.1f}%")
    print(f"Average Latency : {avg_latency:.2f} ms")
    print(f"Max Process RAM : {max_mem:.2f} MB")
    print(f"Min Process RAM : {min(mem_usages):.2f} MB")
    print("--------------------------------------------------")

    if failures > 0:
        print("[!] Stress test failed with execution errors.")
        sys.exit(1)

    if max_mem > 150.0:
        print("[!] Warning: Process memory exceeded 150 MB target budget (excl. LLM model service).")
    else:
        print("[*] Success: Process memory stayed within low-RAM limits (< 150 MB).")

    print("[*] Stress test completed successfully.")

if __name__ == "__main__":
    main()
