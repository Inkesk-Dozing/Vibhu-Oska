# ⚙️Core System Architecture

The backend is built on a "Strategy & Tactics" pattern, separating high-level infrastructure decisions from low-level execution logic.

## 1. High-Level Control: HybridCore

**Role:** The Infrastructure Switch.

**Responsibility:** Determines which system handles the request based on environment health.

**Logic:**

- Checks internet connectivity and server health.
- Routes to MainCore for standard operations.
- Routes to BackupCore if critical failures or network outages are detected.
- Routes to SpecializedCore for specific RAG/Database-only queries.

## 2. The Main Stack (Inside MainCore)

If HybridCore selects the Main Stack, the following modules are activated:

### 🧩 OrchestratorCore (The Manager)

**Role:** Workflow Management.

**Function:** It does not "think"; it directs. It receives the raw request from HybridCore and pushes it through the pipeline (Validation -> Data -> Cognition -> Output).

### 🧠 CognitionCore (The Brain)

**Role:** Intelligence Processing.

**Function:** Stateless processing unit. It accepts sanitized inputs and context, runs them through AI models (LLMs), and returns raw intelligence.

### 🛡️ ValidationCore (The Gatekeeper)

**Role:** Security & Compliance.

**Function:**

- **Input Sanitization:** Sanitizes user data (SQL injection/XSS checks).
- **Output Validation:** Enforces strict adherence to brain.proto and router.proto before data leaves the backend.

### 💾 DataCore (The Memory)

**Role:** Persistence & Context.

**Function:** Handles Vector DB (RAG) lookups and SQL history retrieval. The Orchestrator calls this before calling Cognition to provide context.

### 📊 Monitoring & Optimization

**Role:** System Health and Performance.

**Function:** Handles caching (Redis), prompt compression, and system heartbeat logging.

## 🔄 The Data Lifecycle

Every user request follows a strict "Double-Validation" pipeline to ensure stability and safety.

**Entry Point:** Frontend sends data via router.proto to Backend/EntryPoint.py.

**Infrastructure Check:** EntryPoint.py passes data to HybridCore.

**Decision:** If the system is healthy, activate MainCore.

**Workflow Initialization:** HybridCore passes control to OrchestratorCore.

**Processing Loop:**

- **Step A (Security):** Orchestrator calls ValidationCore to check input safety.
- **Step B (Efficiency):** Orchestrator calls OptimizationCore to check cache.
- **Step C (Context):** Orchestrator calls DataCore to retrieve user history.
- **Step D (Intelligence):** Orchestrator sends (Input + Context) to CognitionCore.
- **Step E (Compliance):** Orchestrator sends AI response to ValidationCore to ensure it matches brain.proto.

**Return:** Orchestrator returns the package to HybridCore -> EntryPoint.py -> Frontend.

## 🛠️ Protocols (Shared)

Communication between Frontend and Backend is strictly typed using Protocol Buffers located in Shared/protos.

- **router.proto:** Defines the envelope for transport (Headers, UserID, TimeStamp).
- **brain.proto:** Defines the structure of the AI payload (Text, Emotions, ActionCodes).
