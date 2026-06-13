"""
Global configuration settings for the Colony of Minds framework.
"""

import os
import sys
from pathlib import Path

# Base directory of the colony project
BASE_DIR = Path(__file__).resolve().parent.parent

# Default SQLite database path for persistent memory log
DEFAULT_MEMORY_DB_PATH = os.environ.get("COLONY_MEMORY_DB_PATH", str(BASE_DIR / "colony_memory.db"))

# Default confidence threshold for verifier rejection
DEFAULT_CONFIDENCE_THRESHOLD = 0.5

# Ollama Model Configurations (Phase 6)
DEFAULT_OLLAMA_PATH = os.environ.get("COLONY_OLLAMA_PATH", "ollama")
DEFAULT_OLLAMA_MODEL = os.environ.get("COLONY_OLLAMA_MODEL", "qwen2.5:1.5b-instruct")
DEFAULT_OLLAMA_API_URL = os.environ.get("COLONY_OLLAMA_API_URL", "http://localhost:11434")
if "unittest" in sys.modules:
    DEFAULT_OLLAMA_MODEL = os.environ.get("COLONY_OLLAMA_MODEL", "")


# CPU/Resource thread limitations (Phase 9 & optimizations)
try:
    OLLAMA_NUM_THREADS = int(os.environ.get("COLONY_OLLAMA_THREADS", "2"))
except ValueError:
    OLLAMA_NUM_THREADS = 2


