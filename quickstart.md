# ⚡ 5-Minute Quickstart

Get up and running with **Colony of Minds AI** in under 5 minutes. This guide covers installation, running a command-line query, and running a custom programmatic agent pipeline.

---

## 📥 1. Installation

Ensure you have Python 3.8+ installed, then clone the repository and install it in editable developer mode:

```bash
# Clone the repository
git clone https://github.com/Jenilsaija/colony-of-minds.git
cd colony-of-minds/maincode

# Create and activate a virtual environment
python -m venv .venv
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install the package in editable mode with development dependencies
pip install -e .[dev]
```

---

## 🖥️ 2. Run via CLI

Test the pipeline immediately using the global command-line shortcuts installed by `pip`:

```bash
# Run a quick math check
colony-run "calculate 45 * 123"
```

### Expected Output:
```text
[*] Router Output: Matches: 'math_op' because of keyword(s) ['calculate'] + arithmetic pattern '45 * 123'
[*] Executing suboperator: math_op
[*] Verifier Output: Verified calculation '45 * 123 = 5535'.
[Final Answer]: The calculation 45 * 123 evaluates to 5535.
```

To start an interactive chat session, run:
```bash
colony-cli
```

---

## 🐍 3. Programmatic & Custom Suboperators

You can define and register your own deterministic or lightweight specialist suboperators. Take a look at the provided [**`quickstart_example.py`**](file:///D:/GitHub/colony_of_minds_phases/maincode/quickstart_example.py):

```python
from colony_ai.run_colony import run_pipeline, register_suboperator, get_operator
from colony_ai.colony.operator import BaseSuboperator
from colony_ai.colony.schemas import SuboperatorResponse

# 1. Define your custom suboperator
class EchoOperator(BaseSuboperator):
    @property
    def name(self) -> str:
        return "echo_op"

    def execute(self, query: str, context: dict = None) -> SuboperatorResponse:
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

# 2. Register and query it
echo_instance = EchoOperator()
register_suboperator("echo_op", echo_instance)

# 3. Execute queries programmatically
resp = get_operator("echo_op").execute("Welcome to Colony of Minds")
print(resp.facts)
```

Run this demo script with:
```bash
python quickstart_example.py
```

---

## 🧪 4. Verify Your Workspace

Make sure all unit tests run successfully on your local environment:

```bash
# Run the complete test suite
python -m unittest discover -s colony_ai/tests -p "test_*.py"

# Run the performance and latency benchmarks
python colony_ai/tests/run_benchmarks.py
```

---

## 🚀 What's Next?
*   Check out the [**`plans/`**](file:///D:/GitHub/colony_of_minds_phases/plans) directory to read the 32-phase architecture design.
*   Read the [**`CONTRIBUTING.md`**](file:///D:/GitHub/colony_of_minds_phases/CONTRIBUTING.md) to see how you can write and submit your own suboperators!
