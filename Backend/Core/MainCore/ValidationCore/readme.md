# ValidationCore

The input/output contract enforcement gate. ValidationCore is called **twice** in every pipeline — once before data retrieval and once after the model generates a response. It enforces structural and semantic rules at both boundaries.

## Responsibility

Fail fast on invalid, dangerous, or malformed content. Never process, never infer — only verify.

## What It Validates

### Input Package
- Prompt exists and is a non-empty string
- Prompt length within configured max (default 4000 chars)
- Prompt does not contain blocked keywords (injection attempts, harmful requests)
- Type field is a valid integer (1=CHAT, 2=CODE, etc.)
- Metadata contains required keys (request_id, session_id, user_id)

### AI Output (TaskResponse)
- `content` field is a non-empty string
- Status code is a valid `StatusCode` enum value
- Token usage fields are non-negative integers
- No internal error markers leaked into content

## Module Boundary Rules

- **No processing logic** — ValidationCore never transforms data, only checks it
- **No external calls** — no DB, no event bus, no model calls
- Returns `(bool, str)` tuples: `(True, "")` on pass, `(False, "reason")` on fail

## Key File

`validation.py` — 4.6KB

## Usage

```python
is_valid, reason = self._validation.validate_input_package(input_pkg)
if not is_valid:
    # publish TASK_FAILED event and return

is_output_valid, out_reason = self._validation.validate_ai_output(response)
if not is_output_valid:
    # publish TASK_FAILED event and return
```
