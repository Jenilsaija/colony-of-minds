# Contributing to Colony of Minds AI

Thank you for your interest in contributing to Colony of Minds AI! We are building a new paradigm for efficient, low-resource cooperative intelligence. Whether you are fixing a bug, adding a new suboperator, optimizing the custom transformer, or fixing a typo in the design documentation, your help is highly appreciated.

---

## 📜 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it to ensure you understand our community standards.

---

## 🛠️ How Can I Contribute?

### 1. Reporting Bugs
*   Check the [Issues](https://github.com/Jenilsaija/colony-of-minds/issues) tab to see if the bug has already been reported.
*   If not, open a new issue. Describe the bug, provide steps to reproduce it, specify the OS and Python version, and paste any error logs. Use our **Bug Report Template**.

### 2. Suggesting Features & Suboperators
*   We welcome new ideas for specialized deterministic suboperators (e.g., regex pattern extractors, symbolic checkers, or lightweight math solvers) that help keep target RAM low.
*   Open an issue explaining the utility of the feature, how it fits into the Router-Suboperator-Atma pipeline, and how it aligns with the 1 GB RAM / 2-core CPU target constraint.

### 3. Submitting Pull Requests
*   **Fork** the repository and create your branch from `main`.
*   Keep your changes focused. If you want to make multiple unrelated changes, submit them as separate Pull Requests.
*   Ensure all existing tests pass and write new tests covering your changes.
*   Submit the Pull Request and fill out the **PR Template** completely.

---

## 💻 Code Style & Standards

To ensure the project remains highly performant, readable, and clean:

### Python Conventions
*   Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines.
*   Use explicit type hinting where possible. The project includes a `pyrightconfig.json` configuration; ensure your IDE does not flag new type warnings.
*   Document classes, methods, and functions with descriptive docstrings.

### Architecture Restrictions
*   **Low Dependency**: Avoid importing large external packages (like heavy vector databases or heavy AI libraries). Keep core dependencies minimal.
*   **Memory Discipline**: Keep memory footprint in mind. Use lazy loading (importing inside functions/classes dynamically) for any component that incurs a process-wide startup memory cost.
*   **No Unnecessary LLMs**: Do not solve problems with LLMs that can be solved deterministically. The verifier and suboperators should be fast and symbolic.

---

## 🧪 Testing Guidelines

Any code changes must be validated against our test suites before a PR can be merged:

### Running Unit Tests
Validate the colony pipeline and the custom model code:
```bash
# Run colony_ai framework tests
python -m unittest discover -s colony_ai/tests -p "test_*.py"

# Run atmacore custom model tests
python -m unittest discover -s atmacore/tests -p "test_*.py"
```

### Running Benchmarks
Ensure that performance (latency and RAM usage) and routing accuracy do not regress:
```bash
# Run the evaluation benchmark
python colony_ai/tests/run_benchmarks.py

# Run the stress-test harness
python colony_ai/tests/stress_test.py
```
*Note: If your change reduces benchmark accuracy or significantly raises latency/RAM, please explain the trade-offs in your PR description.*

---

## 🏷️ Good First Issues for Newcomers

If you are looking to get started, here are a few ideas that are excellent for first-time contributors:

1. **Add new specialized Suboperators**:
   * **`date_op`**: A suboperator that parses natural language dates (e.g., "next Friday") and returns standardized ISO strings.
   * **`regex_op`**: A suboperator designed to match and extract common data patterns (e.g., email, phone numbers, UUIDs) and pass them as facts.
2. **Expand the Verifier rules**:
   * Add check rules to verify structural JSON syntax in code outputs.
   * Extend the contradiction detector to flag opposite assertions (e.g., true vs false).
3. **Enhance CLI experience**:
   * Add colorized terminal formatting (using standard escape codes to avoid extra heavy libraries) to output steps.
4. **Improve Documentation**:
   * Help summarize specific phase plan files or document specific module parameters.

---

## ❓ Need Help?

If you have any questions or want to discuss design ideas before writing code, feel free to open a Discussion on GitHub or reach out to the project maintainers.
