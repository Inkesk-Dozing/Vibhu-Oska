# Notes

## Schemes Used

```markdown
-Camel casing for naming folders and files
-lowercase naming scheme for .md files
-init (empty file init.py)used in each folder for Absolute imports , using it python treats the folder as a package. ---> another method for this though temporary is sys.path append similar to telling this is a root folder too , though better and used for individual scripts.
-Internal Separation:

==================================================================================================

1.Used to separate internal divisions in Class-Functions-

==================================================================================================

-*Rule of Thumb*:
    -Do not put business logic in the OrchestratorCore.
    -Do not put database connections in CognitionCore.
    -Keep BackupCore lightweight and dependency-free.
```

## .venv

The .venv folder serves as the project's virtual environment, isolating dependencies to prevent conflicts with system-wide installations. Its structure includes:

- python/: Contains the Python executable and core files --> **virtualEnvironment for Python**
  - Scripts/ (Windows) or bin/ (Unix): Holds activation scripts and tools like pip.
  - Lib/site-packages/: Stores installed packages and libraries.
-

This setup ensures consistent and reproducible environments across different machines.

## The Environment: "The Editable Install"

Resolved persistent *ModuleNotFoundError* and sys.path workarounds.
**Action Taken**: Created pyproject.toml and executed `pip install -e .`.
**Outcome**: Python recognizes the Backend folder as a globally installed library.
**Benefits**:

- Eliminates fragile relative imports (e.g., ../../Core).
- Enables script execution from any location (Terminal, VS Code, Testing folders).
- Supports absolute imports: `from Backend.Core import ...`, aligning with industry standards for stability.

## protos folder contains the protocols used and its respecful readme

📘 Engineering Log: Modular AI System

1. The Architecture: "Strategy vs. Tactics"
We transitioned from a monolithic script to a Micro-kernel Architecture to distinctly separate decision-making from execution.

### HybridCore (The Strategy Switch)

- **Purpose**: Positioned at the highest level, it assesses system health (Internet/Server status).
- **Rationale**: Prevents main application crashes during outages. If cloud services are unavailable, it seamlessly switches to BackupCore (Local Mode). This isolates "Infrastructure" logic from "Business" logic, ensuring robust resilience.

### OrchestratorCore (The Tactical Manager)

- **Purpose**: Embedded within MainCore, it orchestrates the precise steps of request processing.
- **Rationale**: Maintains clean separation of concerns. The Orchestrator neither "thinks" nor "validates"; it delegates to specialized components.

1. The Components: "Clean Code Principles"
Refactored specific Cores to eliminate "Anthropomorphizing" (human-like code descriptions) and "Over-engineering" (unnecessary nested classes), adhering to best practices for maintainability.

1. The Data Flow: "The Double-Validation Loop"
Established a rigorous lifecycle for each user request to guarantee safety and integrity.

- **Handshake**: Frontend → HybridCore (System health check?) → Orchestrator.
- **Input Guard**: Orchestrator invokes ValidationCore immediately.
  - **Rationale**: Fail fast. Avoid resource waste on malicious or invalid data.
- **Context Retrieval**: Orchestrator engages DataCore.
  - **Rationale**: AI requires memory (History/RAG) for informed responses.
- **Cognition**: Orchestrator dispatches (Input + Context) to CognitionCore.
- **Output Guard**: Orchestrator validates AI Response via ValidationCore.
  - **Rationale**: Ensures AI outputs valid JSON/Protobufs, preventing Frontend crashes.

1. Final Code Structure
Imports are now streamlined and absolute:

```python
# No sys.path hacks. Pure Python.
from Backend.Core.MainCore.ValidationCore.validation import ValidationCore
from Backend.Core.MainCore.CognitionCore.cognition import CognitionCore
from Backend.Core.SpecializedCore.DataCore.datacore import DataCore
```

**Next Step**: Implement DataCore logic for database connectivity, assured that the system handles routing, safety, and error management effectively.
