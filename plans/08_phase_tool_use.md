# Phase 8: Tool Use Layer

## Goal

Allow suboperators to use external tools safely.

Tools turn the system from a text generator into an operator.

## Tool examples

- calculator
- Python code runner
- shell command runner
- file reader
- web/API fetcher
- database query
- email sender
- Telegram sender
- calendar tool

## Tool safety levels

### Safe tools

Can run automatically:

- arithmetic calculator
- regex extractor
- read-only local search
- date/time lookup

### Medium-risk tools

Need constraints:

- file writes
- code execution
- web requests
- database queries

### High-risk tools

Need explicit confirmation:

- deleting files
- sending messages
- spending money
- deploying code
- changing production data

## Tool call record

Every tool call should produce a log:

```json
{
  "tool": "calculator",
  "input": "45 * 123",
  "output": 5535,
  "success": true,
  "duration_ms": 2
}
```

## Tool result verification

Verifier should inspect tool results before Atma sees them.

Example:

- calculator result can be trusted high-confidence
- web result needs source URL
- shell output needs exit code
- file read needs path and timestamp

## Success criteria

Prompt:

```text
Calculate 45 * 123 using tool.
```

Tool log:

```json
{
  "tool": "calculator",
  "input": "45 * 123",
  "output": 5535,
  "success": true
}
```

Atma answer:

```text
45 * 123 = 5535.
```
