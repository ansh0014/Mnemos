# Mnemos: Engineering Remaining Work Analysis (`left.md`)

> **Platform Completion Status**: **65% Complete** (Core Foundation & Native UI) | **35% Remaining** (Agent Core, Gateway & Sandbox)

---

## 📊 Executive Status Overview

```
[█████████████████████████████████░░░░░░░░░░░░░░░░░] 65% Completed

✅ COMPLETED (65%):
  ├── Document Ingestion & Structure Extraction (PyMuPDF, EPUB, chapters.py)
  ├── Multi-Provider Model Client Adapters (Anthropic, OpenAI, OpenRouter, Ollama)
  ├── Native macOS 14+ & iPadOS 17+ SwiftUI Client Shell & Menu Bar
  ├── Pip Procedural Character Rig & Physics Engine (PipRig.swift)
  ├── FSRS-4.5 Spaced Repetition Math & State Transitions (FSRS.swift)
  ├── Dual-Device Cloud Sync Engine via Google Drive AppData (SyncEngine.swift)
  ├── Reading Telemetry, Dwell Time, & Anti-Skim Verification (ReadingCredit.swift)
  └── Anti-Guilt Nudge Engine & Quiet-Hours Dispatcher (Nudges.swift)

🚧 REMAINING WORK (35%) — PRIMARY FOCUS: AGENTIC INFRASTRUCTURE:
  ├── 1. Uber-Style Model Context Protocol (MCP) Gateway (Control & Data Planes)
  ├── 2. Google DeepMind Token Optimization Engine (Pruning, Projection, KV Alignment)
  ├── 3. Multi-Tier Cognitive Memory Engine (Episodic, Semantic, Procedural, Vector)
  ├── 4. In-Situ Conversational Active Reading Co-Pilot (Code Synthesis & Reality Checks)
  ├── 5. Socratic Recall Diagnostic Agent (Semantic Grading & Misconception Probing)
  ├── 6. Interactive Verification Sandbox (Deterministic Virtual Shims & Test Matrix)
  └── 7. Native Swift Client Bridge for Agent RPC & Streaming Drawers
```

---

## 🏛️ Part 1: Reality Check — What is Already Done (65%)

The platform is **not** starting from scratch. The foundational storage, parsing, native rendering, and scheduling layers are fully functional and tested.

| Subsystem | Source Location | Status | What is Operational |
| :--- | :--- | :---: | :--- |
| **Chapter Parser** | `pipeline/neuralloop_books/chapters.py` (36 KB) | ✅ 100% | Extracts TOC, parses EPUB/PDF, preserves nested code blocks and heading trees. |
| **Atomic File State** | `pipeline/neuralloop_books/pipeline.py` (12 KB) | ✅ 100% | Atomic transactional updates for `book.json`, idempotency guards, checksums. |
| **Concept Graph Parser** | `pipeline/neuralloop_books/book_graph.py` (4 KB) | ✅ 80% | Extracts concept nodes and dependency edges from raw chapter text. |
| **Model Connectors** | `pipeline/neuralloop_books/models/` | ✅ 85% | Unified adapter layer for Anthropic, OpenAI, OpenRouter, and Ollama. |
| **FSRS-4.5 Algorithm** | `apple/Sources/NeuralLoopCore/FSRS.swift` (3 KB) | ✅ 100% | Complete spaced repetition math (stability, difficulty, retrievability decay). |
| **5-Stage State Machine** | `apple/Sources/NeuralLoopCore/Loop.swift` (2 KB) | ✅ 90% | Enforces stage unlocking rules and loop completion criteria. |
| **Sync Engine** | `apple/Sources/NeuralLoopCore/SyncEngine.swift` (50 KB) | ✅ 95% | Google Drive `appdata` sync, CRDT delta resolution, offline cache replay. |
| **Pip Companion Rig** | `apple/Sources/NeuralLoopCore/PipRig.swift` (8 KB) | ✅ 100% | Procedural bone rigs, eye tracking, mood poses (read, proud, nap, study). |
| **Nudge Controller** | `apple/Sources/NeuralLoopCore/Nudges.swift` (22 KB) | ✅ 100% | Anti-guilt nudge policies, quiet hour calculation, local notification hooks. |
| **Dwell Telemetry** | `apple/Sources/NeuralLoopCore/ReadingCredit.swift` (7 KB) | ✅ 100% | Scroll velocity, viewport intersection tracking, reading credit verification. |

---

## 🤖 Part 2: Detailed Agent Work Left (The 35%)

The remaining engineering work is centered on building the **Agent Architecture**, **Uber MCP Gateway**, **DeepMind Token Optimizer**, and **Interactive Verification Sandbox**.

```
                           ┌──────────────────────────────────────────────┐
                           │            AGENT WORK REMAINING              │
                           └──────────────────────┬───────────────────────┘
                                                  │
         ┌───────────────────┬────────────────────┼───────────────────┬───────────────────┐
         ▼                   ▼                    ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   UBER MCP      │ │   DEEPMIND      │ │   MULTI-TIER    │ │   IN-SITU       │ │   SANDBOX       │
│   GATEWAY       │ │   OPTIMIZER     │ │   MEMORY        │ │   CO-PILOT      │ │   VERIFICATION  │
│                 │ │                 │ │                 │ │                 │ │                 │
│ • Registry      │ │ • Schema Prune  │ │ • Episodic Log  │ │ • "Show in Code"│ │ • VirtualClock  │
│ • Proxy Router  │ │ • Field Project │ │ • Graph Memory  │ │ • Reality Check │ │ • Fault Inject  │
│ • Circuit Break │ │ • KV Align (4k) │ │ • Proc. Recipes │ │ • Margin Notes  │ │ • Test Runner   │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

### Task 1: Uber-Inspired Model Context Protocol (MCP) Gateway
**Goal**: Decouple agents from direct tool bindings to prevent context explosion and enable dynamic multi-agent capability routing.

- [ ] **1.1 Control Plane Tool Registry (`pipeline/gateway/registry.py`)**:
  - Implement dynamic tool registration with semantic tags (`stage:read`, `stage:recall`, `stage:harness`).
  - Add intent-based capability discovery: dynamically expose only tools matching active intent instead of registering all tools globally into the system prompt.
  - Implement token budget tracking per tool definition.
- [ ] **1.2 Data Plane Proxy Router (`pipeline/gateway/router.py`)**:
  - Standardize JSON-RPC 2.0 communication over local stdio / Unix domain socket.
  - Build tenant and role isolation: agents cannot execute unauthorized tools outside their active phase.
  - Implement circuit breakers and retry policies with exponential backoff for external tools.
- [ ] **1.3 Built-in Agent Tools (`pipeline/gateway/tools/`)**:
  - `graph_query_tool`: query concept prerequisites and descendants.
  - `code_runner_tool`: run student code in the verification sandbox.
  - `reality_check_tool`: query production post-mortems and distributed systems failure archives.

---

### Task 2: Google DeepMind Token Optimization Engine
**Goal**: Reduce context window consumption by 60–80% and increase KV cache reuse across turns.

- [ ] **2.1 Dynamic Schema Pruner (`pipeline/optimizer/schema_pruner.py`)**:
  - Strip redundant parameter descriptions and JSON Schema boilerplate when calling models with high-certainty intents (-45% schema overhead).
  - Compress multi-line parameter definitions into compact inline signatures.
- [ ] **2.2 Response Field Projection (`pipeline/optimizer/projector.py`)**:
  - Implement a `fields=[...]` filter on all gateway tool outputs, ensuring the LLM context only receives fields explicitly requested by the agent rather than raw 10KB tool payloads.
- [ ] **2.3 KV Cache Prefix Alignment (`pipeline/optimizer/kv_aligner.py`)**:
  - Pad and align static system prompts, role instructions, and tool definitions to fixed 4096-token boundary blocks.
  - Enforce strict append-only structures for conversation history to maximize hardware KV cache hits (>80% reuse rate).
- [ ] **2.4 Semantic Context Compaction (`pipeline/optimizer/compactor.py`)**:
  - Sliding-window summarizer that rolls older reading chat turns into structured factual delta vectors while preserving active code references.

---

### Task 3: Multi-Tier Cognitive Memory Engine
**Goal**: Give reading, recall, and harness agents continuous contextual awareness across chapters without saturating the prompt window.

- [ ] **3.1 Episodic Memory Store (`pipeline/memory/episodic.py`)**:
  - SQLite/PG-lite table logging timestamped user interactions: failed harness assertions, repeated reading confusions, and previous recall explanations.
  - Exponential time-decay relevance scoring: retrieve recent failures with higher priority during study sessions.
- [ ] **3.2 Semantic Memory Graph (`pipeline/memory/semantic.py`)**:
  - Query layer over `book_graph.py` output.
  - Traversal methods: `get_prerequisites(concept_id)`, `get_downstream_dependents(concept_id)`, and `find_missing_links(student_explanation)`.
- [ ] **3.3 Procedural Memory Engine (`pipeline/memory/procedural.py`)**:
  - Reusable execution blueprints: debugging workflows, verification challenge boilerplates, and step-by-step algorithms.
- [ ] **3.4 Local Vector Grounding (`pipeline/memory/vector_index.py`)**:
  - Fast on-device embedding generation using small local models (`all-MiniLM-L6-v2` or `bge-small-en-v1.5`) via PyTorch/ONNX runtime.
  - Cosine similarity search over indexed chapter chunks and book glossary.

---

### Task 4: In-Situ Conversational Active Reading Co-Pilot (Stage 2)
**Goal**: Transform passive chapter reading into an active, conversational coding lab.

- [ ] **4.1 Co-Pilot Dispatcher (`pipeline/agents/reader_copilot.py`)**:
  - Contextual prompt builder that injects: (a) currently visible chapter section, (b) relevant concept dependencies from Semantic Memory, and (c) student's past failure logs from Episodic Memory.
- [ ] **4.2 "Show Me in Code" Engine (`pipeline/agents/code_explainer.py`)**:
  - Converts theoretical paragraphs into runnable, minimal Python/Go/Rust implementations with zero unnecessary external dependencies.
- [ ] **4.3 "Production Reality Check" Engine (`pipeline/agents/reality_check.py`)**:
  - Synthesizes real-world production incident reports (e.g. AWS DynamoDB partition splits, Cloudflare DNS leaks, Redis cluster failover stalls) directly related to the chapter topic.
- [ ] **4.4 Proactive Socratic Margin Notes (`pipeline/agents/margin_notes.py`)**:
  - Analyzes dense sections and generates 1-sentence thought-provoking margin questions to prevent passive skimming.

---

### Task 5: Socratic Diagnostic Agent (Stage 3 Recall)
**Goal**: Rigorous active verbal retrieval evaluation beyond multiple-choice quizzes.

- [ ] **5.1 Semantic Rubric Grader (`pipeline/agents/socratic_grader.py`)**:
  - Compares student's free-text explanation against the chapter's extracted invariant checklist.
  - Scores coverage: Core Principle (40%), Invariant/Edge Case (30%), Trade-offs (30%).
- [ ] **5.2 Misconception & Anti-Pattern Classifier**:
  - Detects subtle engineering confusions (e.g., conflating Paxos synod with multi-paxos log replication, or mixing up linearizability with serializability).
- [ ] **5.3 Adaptive Follow-Up Question Generator**:
  - If score is between 40% and 80%, generates a single, hyper-targeted probing question rather than giving away the answer.

---

### Task 6: Interactive Verification Sandbox (Stage 4 Harness)
**Goal**: Hands-on systems engineering testing environment running code against deterministic simulated failures.

- [ ] **6.1 Execution Sandbox Runner (`pipeline/sandbox/runner.py`)**:
  - Isolated subprocess executor with strict CPU time (max 3s) and memory caps (max 256MB).
  - Streaming stdout/stderr output via JSON-RPC.
- [ ] **6.2 Deterministic Virtual Shims (`pipeline/sandbox/shims/`)**:
  - `VirtualClock`: Controllable mock clock to test timeouts, heartbeats, and leader election leases without `sleep()`.
  - `VirtualStorage`: Fault-injecting file system (simulates torn writes, out-of-space, and delayed fsyncs).
  - `VirtualNetwork`: Deterministic network simulator (drops packets, injects asymmetric partitions, introduces latency jitter).
- [ ] **6.3 Challenge Matrix & Grading Engine (`pipeline/sandbox/evaluator.py`)**:
  - Pre-defined test suites for classical problems (e.g., implement a thread-safe LRU cache, build a Vector Clock conflict resolver, write a 2-Phase Commit coordinator).

---

### Task 7: Native Swift Client Agent Integration
**Goal**: Surface agent capabilities seamlessly in the macOS and iPadOS SwiftUI apps.

- [ ] **7.1 Local Subprocess Agent Bridge (`apple/App/Services/AgentBridge.swift`)**:
  - Stdio JSON-RPC client in Swift communicating with the Python MCP Gateway.
  - Streaming response support for SSE / chunked token output.
- [ ] **7.2 Active Reader Split-Pane Co-Pilot (`apple/App/Views/ReaderCoPilotView.swift`)**:
  - Sliding side-panel in the reading view displaying in-situ conversational responses.
  - "Insert to Sandbox" and "Copy Implementation" action buttons.
- [ ] **7.3 Interactive Verification Terminal (`apple/App/Views/HarnessTerminalView.swift`)**:
  - Code editor (Monaco or native SwiftUI syntax highlighter) with "Run Verification Tests" trigger.
  - Real-time test result matrix (Pass/Fail green-red indicators for partition tests, crash-recovery tests).
- [ ] **7.4 Pip Companion State Reactions**:
  - Connect Pip animations to agent states: Pip concentrates during test suite execution, celebrates on all tests passing, and tilts head inquisitively on recall misconceptions.

---

## 📅 Part 3: Phase-by-Phase Execution Roadmap

```
PHASE 1: Gateway & Optimization Engine           [Sprint 1-2]
├── Implement MCP Tool Registry & Router
├── Build DeepMind Schema Pruner & Response Projector
└── Establish 4k KV Cache Alignment Rules

PHASE 2: Multi-Tier Memory & Stage 2 Co-Pilot     [Sprint 3-4]
├── Implement SQLite Episodic Store & Semantic Graph Query Layer
├── Build "Show Me in Code" & "Reality Check" prompt pipelines
└── Connect Swift Reader View to Agent Bridge

PHASE 3: Socratic Recall & Diagnostic Agent       [Sprint 5]
├── Build Rubric Evaluation & Misconception Classifier
└── Integrate Follow-Up Socratic Probing in Swift Recall UI

PHASE 4: Verification Sandbox & Systems Shims     [Sprint 6-7]
├── Build Subprocess Sandbox Runner
├── Implement VirtualClock, VirtualStorage, VirtualNetwork shims
└── Wire Challenge Matrix & Pip celebratory triggers
```

---

## 🎯 Summary Checklist

| Component | Priority | Complexity | Target Sprint |
| :--- | :---: | :---: | :---: |
| **Uber MCP Gateway** | P0 | Medium | Sprint 1 |
| **DeepMind Token Optimizer** | P0 | Medium | Sprint 2 |
| **Stage 2 Active Reader Co-Pilot** | P0 | Low | Sprint 3 |
| **Multi-Tier Cognitive Memory** | P1 | High | Sprint 4 |
| **Stage 3 Socratic Evaluator** | P1 | Medium | Sprint 5 |
| **Stage 4 Verification Sandbox** | P1 | High | Sprint 6 |
| **Swift UI Client RPC Integration** | P1 | Medium | Sprint 7 |
