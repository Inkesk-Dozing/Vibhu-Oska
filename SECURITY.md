# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `0.2.x` (current) | Yes |
| `0.1.x` | No — upgrade to 0.2.x |

---

## Reporting a Vulnerability

**Do not open a public GitHub Issue for security vulnerabilities.**

If you discover a security issue — including but not limited to authentication bypasses,
injection vulnerabilities, unsafe deserialization, or exposure of local system resources —
please report it privately using one of the following channels:

- **Email:** inkeskdozing@gmail.com
- **Subject line:** `[SECURITY] Vibhu-Oska — <brief description>`

You will receive an acknowledgment within **48 hours** and a resolution timeline within
**7 days** of the initial report.

Please include in your report:
- A clear description of the vulnerability and its potential impact.
- Steps to reproduce, including any relevant code snippets or request payloads.
- The version or commit hash where the issue was observed.
- (Optional) A suggested fix or mitigation.

---

## Security Model

Vibhu-Oska is designed as a **locally-executed, offline-first system**. Understanding
its threat model helps assess the risk surface:

### What is in scope

- SQL injection through user-provided chat input reaching `DatabaseConnector` queries.
- XSS payloads stored in the knowledge graph and reflected in the frontend UI.
- Path traversal through corpus append or file-read endpoints.
- WebSocket session hijacking or unauthorized cross-session data access.
- Unsafe deserialization of incoming JSON or Protobuf payloads.
- Privilege escalation through the `AutomationCore` OS command execution interface.

### What is out of scope

- Vulnerabilities that require physical access to the host machine.
- Issues in third-party dependencies (report those upstream to the relevant maintainer).
- Denial-of-service attacks against a locally-running single-user instance.
- Security issues in the private Sovereign GPT weights or biometric calibration data
  (these are not distributed in this repository).

---

## Security Measures in the Codebase

- **Input sanitization**: `ValidationCore` strips SQL injection patterns and HTML tags
  from all user-provided input before it reaches any downstream module.
- **Output validation**: Every `TaskResponse` is schema-checked by `ValidationCore`
  before it leaves the pipeline and reaches the WebSocket client.
- **No hardcoded credentials**: All secrets are loaded via `.env` — never committed.
  `.env.example` provides the required variable names with placeholder values only.
- **Parameterized queries**: `DatabaseConnector` uses SQLite parameterized statements
  exclusively. No string interpolation in SQL.
- **CORS**: The FastAPI gateway restricts origins in non-development environments.

---

## Dependency Scanning

We recommend running the following before deploying:

```bash
# Check for known CVEs in dependencies
pip-audit

# Scan for hardcoded secrets
trufflehog filesystem .

# Static analysis
ruff check .
```
