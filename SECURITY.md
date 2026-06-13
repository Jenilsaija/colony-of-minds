# Security Policy

We take the security of Colony of Minds AI seriously. If you believe you have found a security vulnerability in this project, please report it to us using the instructions below.

---

## Supported Versions

Only the latest release (and active development on the `main` branch) is actively supported with security updates.

| Version | Supported |
| ------- | --------- |
| >= 0.1.x| ✅ Yes     |
| < 0.1.0 | ❌ No      |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

If you discover a vulnerability, please report it privately:
1. Email your findings to **support@sparktac.in**.
2. Include a detailed description of the vulnerability, the components involved (e.g., specific tool permissions, shell runners, verifier bypass), steps to reproduce, and a proof of concept (PoC) if available.

We will acknowledge receipt of your report within 48 hours and work with you to analyze and resolve the issue.

---

## Core Security Assumptions & Guidelines

Colony of Minds AI is designed to run locally and orchestrate actions through suboperators and tools. To protect your system:
*   **Tool Executions**: The shell runner and file deleter tools contain permission gates. Do not disable or bypass these safety gates in production environments.
*   **Arbitrary Inputs**: Be cautious when running the Colony framework on untrusted user input, as malicious commands or paths could be passed to tools if the routing and verification logic is tampered with.
