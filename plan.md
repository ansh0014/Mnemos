# Mnemos: Master Product & Technical Architecture Plan
## From Document Ingestion to Long-Term Cognitive Mastery

---

## 1. Executive Summary & Codebase Reality Audit

### 1.1 The Reality: 65% of Mnemos is Already Built and Operational
**Mnemos** is an adaptive, learner-centric AI learning platform engineered specifically for software developers, engineers, and technical researchers. It transforms complex educational documents—textbooks, research papers, lecture slides, technical manuals, and programming guides—into an automated, personalized cognitive journey from initial understanding to permanent retention.

**Critical Architectural Pivot:** We have removed slow, heavy media pipelines (**eliminating neural voice synthesis, audio mixing, and video rendering**). This makes Mnemos **instantaneous, lightweight, and 100% portable**. Books are represented as rich semantic text, interactive diagrams, and executable code rather than hundreds of megabytes of media files.

The master architecture unites the existing 65% foundation with five high-impact pillars:
1. **Uber's MCP Gateway Pattern:** Decoupling 5 specialized AI learning agents from raw tools and backend services via a strict **Control Plane (Role-Based Tool Registry & Governance)** and **Data Plane (Proxy Routing & Response Projection)**.
2. **Google DeepMind's Token Optimization Principles:** Eliminating context window bloat, reducing latency by up to 70%, and cutting inference costs via **Semantic Context Compaction, KV Cache Prefix Alignment, Response Projection, and Dynamic Schema Pruning**.
3. **Conversational Active Reading (The In-Situ Developer Co-Pilot):** Transforming passive reading into an interactive dialogue embedded directly alongside the text with developer quick actions: *"Show Me in Code"*, *"Production Reality Check"*, and proactive Socratic margin interventions.
4. **Interactive Verification Sandbox (The Harness Engine):** Providing an isolated code and simulation sandbox where learners run code, observe failure modes under stress, and verify architectural invariants.
5. **Advanced Multi-Tier Memory System (Mem0 + Relational):** Separating memory into distinct cognitive tiers—**Episodic** (what happened), **Semantic** (what is understood/misunderstood), **Procedural** (how the learner learns), **Isolated Document Grounding**, and an **In-Memory KV Cache**.

```mermaid
flowchart LR
    subgraph BuiltCore ["Layer 1: Existing Built Core (65% COMPLETED)"]
        direction LR
        P1["PDF / EPUB Chapter Splitter<br>(chapters.py)"]
        P2["Multi-Lane Pipeline<br>(pipeline.py, state.py)"]
        P3["Model Adapters<br>(Ollama, OpenAI, Claude, NotebookLM)"]
        P4["FSRS-4.5 Scheduler<br>(FSRS.swift / Python Core)"]
        P5["Knowledge Graph Builder<br>(book_graph.py)"]
        P6["Apple UI & Telemetry<br>(SwiftUI & Anti-Cheat Coverage)"]
        P7["Pip Sprite Rig<br>(pip-rig.json, 8 poses, nudges)"]
    end

    subgraph NewArchitecture ["Layer 2: Architectural Extensions (35% TO COMPLETE)"]
        direction LR
        N1["Uber-Inspired MCP Gateway<br>(mcp_gateway.py: Proxy & Registry)"]
        N2["DeepMind Token Optimizer<br>(Compaction & KV Prefix Alignment)"]
        N3["In-Situ Reading Co-Pilot<br>(Code Gen & War Stories)"]
        N4["Multi-Tier Memory Engine<br>(Episodic, Semantic, Procedural)"]
        N5["Verification Sandbox<br>(Virtual Shims & Stress Harness)"]
    end

    BuiltCore --> NewArchitecture
```

---

## 2. Product Vision & Positioning

### 2.1 Mission Statement
> **"Turn every technical document into an adaptive learning journey, from initial understanding to production intuition and long-term mastery."**

Mnemos is designed for knowledge workers, developers, engineers, and serious students who tackle dense, high-stakes material. It rejects both passive reading (which creates an illusion of competence) and aggressive, guilt-driven gamification (which causes burnout).

### 2.2 Product Positioning Matrix

```
       ▲ High Memory & Cognitive Retention
       │
       │                                     ★ Mnemos
       │                                       (Learner-Centric Lifecycle:
       │                                        5-Stage Loop + Dual Memory
       │                                        + MCP Gateway + Sandbox)
       │               Anki
       │         (Deterministic FSRS,
       │          Manual, No Ingestion)
       │                                       Google NotebookLM
       │                                       (Source-Centric Research,
       │                                        Amnesic)
       │     Kindle / Acrobat
       │     (Passive Consumption,             YouLearn.ai
       │      Zero Retention Engine)           (Study-Centric SaaS Toolkit)
       └─────────────────────────────────────────────────────────────►
       Low Automation / High Friction          High AI Automation
```

---

## 3. High-Level Design (HLD): End-to-End System Architecture

```mermaid
flowchart LR
    subgraph UI ["1. Native Apple UI & Companion (ALREADY BUILT)"]
        direction LR
        MacUI["macOS / iPadOS SwiftUI<br>(Pip Companion, 5 Stages)"]
        DriveSync["Google Drive AppData Sync<br>(Zero-Server-Cost Bridge)"]
    end

    subgraph Gateway ["2. Uber-Inspired MCP Gateway (DATA & CONTROL PLANE)"]
        direction LR
        Registry["Control Plane Registry<br>(Discovery != Exposure)"]
        Projector["DeepMind Token Optimizer<br>(Compaction & Projection)"]
        Proxy["Proxy Router & Dispatcher"]
        Registry --> Proxy
        Proxy --> Projector
    end

    subgraph Agents ["3. 5 Stage-Specialized AI Agents"]
        direction LR
        A1["1. Prime Agent<br>(Concept Briefing)"]
        A2["2. Read Co-Pilot Agent<br>(Active Dialogue & Code)"]
        A3["3. Recall Agent<br>(Socratic Diagnosis)"]
        A4["4. Harness/Map Agent<br>(Verification Sandbox)"]
        A5["5. Remember Agent<br>(FSRS Spaced Review)"]
    end

    subgraph MemoryEngine ["4. Advanced Multi-Tier Memory Engine"]
        direction LR
        M_Epi["Episodic Memory<br>(Sessions & Logs)"]
        M_Sem["Semantic Memory<br>(Misconceptions & Mastery)"]
        M_Pro["Procedural Memory<br>(Learner Strategies)"]
        M_RAG["Isolated Document Grounding<br>(SQLite FTS5 + Embeddings)"]
        M_KV["KV Prompt Cache<br>(Prefix Alignment)"]
    end

    subgraph SandboxEngine ["5. Verification & Code Sandbox"]
        direction LR
        WasmBox["Isolated Execution Sandbox<br>(Deterministic Watchdog)"]
        SimTrace["Stress Simulation Harness<br>(Telemetry & Trace Frames)"]
    end

    MacUI <--> Gateway
    Gateway <--> Agents
    Gateway <--> MemoryEngine
    Gateway <--> SandboxEngine
    MacUI <--> DriveSync
```

---

## 4. The Modernized 5-Stage Cognitive Pipeline

```mermaid
flowchart LR
    S1["Stage 1: PRIME<br>Rapid Concept Briefing & Problem Framing"] --> S2["Stage 2: CONVERSATIONAL ACTIVE READ<br>In-Situ AI Co-Pilot with Code & War Stories"]
    S2 --> S3["Stage 3: SOCRATIC RECALL<br>Explain in Own Words; Agent Diagnoses"]
    S3 --> S4["Stage 4: INTERACTIVE HARNESS<br>Run Code Sandbox & Reconstruct Schema"]
    S4 --> S5["Stage 5: REMEMBER & SPACE<br>Deterministic FSRS-4.5 Flashcard Reviews"]
    S5 --> NextLoop["🎉 Loop Closed<br>Next Chapter Unlocks"]
```

### 4.1 Stage 1: Prime (Executive Concept Briefing & Problem Framing)
* **What happens:** Before reading, the learner gets a **60-second architectural briefing**:
  * **Core Problem Statement:** What fundamental system constraint forced this concept to exist?
  * **Two-Engineer Dialogue Transcript:** A rapid text-based exchange between Ada (the curious engineer) and Theo (the senior staff architect) explaining the core intuition and trade-offs.
  * **Schema Teaser:** A visual dependency diagram introducing the key components.
* **Why Drop Heavy Audio/Video:** Developers read 3x faster than listening to audio. Removing neural voice synthesis and video rendering cuts chapter preparation time from 8 minutes down to **1.5 seconds**, eliminates heavy dependencies (FFmpeg, Chromium, PyAV, audio codecs), and keeps the storage footprint under a few kilobytes.

### 4.2 Stage 2: Conversational Active Reading (The In-Situ Developer Co-Pilot)
* **What happens:** The learner reads the source text in a dual-pane workspace accompanied by an intelligent in-situ co-pilot:

```mermaid
flowchart LR
    subgraph ActiveReaderUI ["Dual-Pane Active Reader Interface"]
        direction LR
        LeftBook["Left Pane: Source Document<br>• Clean typography & code blocks<br>• Highlight / select any paragraph<br>• Reading telemetry (scroll & time)"]
        RightCoPilot["Right Pane: In-Situ Conversational Co-Pilot<br>• Instant contextual dialogue<br>• 'Show Me in Code' generator<br>• 'Production War Stories' (Kafka, Postgres)<br>• Proactive Socratic margin notes"]
    end

    LeftBook <-->|"Scroll Position & Selected Claim"| RightCoPilot
```

* **Core Developer Capabilities:**
  1. **Instant Contextual Anchoring:** Co-Pilot tracks active scroll position and selected paragraphs. Zero copy-pasting to a separate ChatGPT window.
  2. **Developer Quick Actions:**
     * 💻 **"Show Me in Code":** Converts abstract textbook theory (e.g., Paxos leader election, 2-Phase Locking, LSM-tree compaction) into a 15-line executable code snippet in Python, Go, TypeScript, or Rust.
     * 🏭 **"Production Reality Check":** Explains where and how real systems (RocksDB, Kafka, Linux kernel) implement or fail on the concept.
     * ⚖️ **"Devil's Advocate & Trade-Offs":** Highlights edge cases, hardware faults, and hidden assumptions.
     * 🧪 **"Spin Up Inline Sandbox":** Injects an interactive code playground directly beneath the paragraph so you can tweak parameters and see output immediately.
  3. **Proactive Socratic Margin Notes ("Whispers"):** Drops interactive pills after dense proofs to check comprehension before you scroll past.
  4. **DeepMind Token Optimization:** Streaming latency $<400\text{ms}$ with pinned KV prompt prefix caching.

### 4.3 Stage 3: Socratic Recall (Active Retrieval Practice)
* **What happens:** The user is asked to explain the core mechanism in their own words. The Recall Agent checks key claims against ground truth, flags misunderstandings, and responds with Socratic counter-questions without spoiling the answer.
* **Cognitive Science:** **The Generation Effect** (Roediger & Karpicke). Producing an explanation from memory creates 3x stronger memory consolidation than passive review.

### 4.4 Stage 4: Interactive Harness & Schema Reconstruction
* **What happens:** The learner bridges theory into working intuition:
  * **For Systems & Codebooks:** The learner runs code in the **Verification Sandbox**, sees it break under realistic stress (e.g. burst traffic or node failure), diagnoses the root cause, and observes the natural fix.
  * **For Conceptual Textbooks:** The learner actively reconstructs the chapter's concept dependency graph from memory like a jigsaw puzzle.
* **Cognitive Science:** **Schema Construction & Cognitive Load Theory** (Sweller). Knowledge is converted from isolated episodic facts into connected relational schemas.

### 4.5 Stage 5: Remember & Space (Long-Term Retention)
* **What happens:** Flashcards generated from the chapter—specifically prioritized around the learner's diagnosed misconceptions—are scheduled on a mathematical curve.
* **Math Engine:** **Deterministic FSRS-4.5** calculates Stability ($S$), Difficulty ($D$), and Retrievability ($R$). Reviews are served right before memory drops below 90% retrievability.

---

## 5. Low-Level Design (LLD): Uber-Inspired MCP Gateway

```mermaid
flowchart LR
    subgraph ControlPlane ["Control Plane (Registry & Governance)"]
        direction LR
        ToolCatalog["Tool Registry<br>(Metadata, Schemas, Ownership)"]
        RolePolicy["Role-Scoped Access Matrix<br>('Discovery != Exposure')"]
        ToolCatalog --> RolePolicy
    end

    subgraph DataPlane ["Data Plane (Proxy & Runtime Engine)"]
        direction LR
        ProxyRouter["Proxy Router & Load Balancer"]
        DeepMindOptimizer["DeepMind Token Optimizer<br>(Compactor & Field Projector)"]
        ProtocolBridge["Protocol Translation<br>(MCP JSON-RPC to Native Drivers)"]
        ProxyRouter --> DeepMindOptimizer
        DeepMindOptimizer --> ProtocolBridge
    end

    RolePolicy --> ProxyRouter
```

### Role-Scoped Tool Visibility Matrix
* **Prime Agent:** Accesses `get_chapter_summary`, `generate_dialogue_briefing`.
* **Read Co-Pilot Agent:** Accesses `get_active_section`, `lookup_glossary`, `generate_code_example`, `get_production_war_story`.
* **Recall Agent:** Accesses `query_ground_truth`, `get_learner_misconceptions`, `log_misconception_resolution`.
* **Harness & Map Agent:** Accesses `run_sandbox_code`, `inject_simulation_fault`, `get_concept_graph`.
* **Remember Agent:** Accesses `get_due_cards`, `record_fsrs_review`, `create_atomic_card`.

---

## 6. Low-Level Design (LLD): Multi-Tier Cognitive Memory Engine

```mermaid
erDiagram
    LEARNER_PROFILE ||--o{ CONCEPT_MASTERY : maintains
    LEARNER_PROFILE ||--o{ MISCONCEPTIONS : diagnoses
    LEARNER_PROFILE ||--o{ RECALL_SESSIONS : logs
    CONCEPT_MASTERY ||--o{ FSRS_CARDS : schedules

    LEARNER_PROFILE {
        string user_id PK
        string preferred_learning_style
        float global_retention_score
        timestamp last_synced
    }

    CONCEPT_MASTERY {
        string concept_id PK
        string domain
        string canonical_name
        float mastery_score
        int total_recall_attempts
        int failed_recall_attempts
        timestamp last_tested_at
    }

    MISCONCEPTIONS {
        string id PK
        string concept_id FK
        string diagnosis_summary
        string triggering_pattern
        boolean resolved
        timestamp created_at
        timestamp resolved_at
    }

    RECALL_SESSIONS {
        string id PK
        string document_id
        int chapter_index
        string prompt_text
        string user_response
        float awarded_score
        string socratic_feedback
        timestamp timestamp
    }

    FSRS_CARDS {
        string card_id PK
        string concept_id FK
        float stability
        float difficulty
        int reps
        int lapses
        timestamp due_timestamp
        int current_state
    }
```

---

## 7. Low-Level Design (LLD): Interactive Verification Sandbox

```mermaid
flowchart LR
    UserCode["Learner Code (TypeScript / Python)"] --> Sandbox["Isolated Execution Sandbox (Web Worker / Wasm / Subprocess)"]
    
    subgraph SandboxInternals ["Sandbox Runtime & Virtual Shims"]
        direction LR
        Watchdog["1.5s Watchdog<br>(Prevents Infinite Loops)"]
        Shims["Virtual Shim Registry<br>• Virtual Clock (Deterministic time)<br>• Virtual Storage (Byte-log & seeks)<br>• Virtual Network (Latency & partitions)"]
    end

    Sandbox --> SandboxInternals
    SandboxInternals --> StressTest["Deterministic Stress Scenario<br>(Traffic bursts / Fault injections)"]
    StressTest --> TelemetryFrames["SimulationTrace Frames<br>• timeline_stream<br>• state_xray<br>• topology_graph"]
    TelemetryFrames --> NativeUI["Visual Render in Apple UI"]
```

---

## 8. Focused 4-Week Delivery Roadmap (Completing the Remaining 35%)

Because heavy audio synthesis and video rendering are eliminated, the system is dramatically simpler to build and maintain:

| Week | Focus Area | Deliverables to Build | Base Code Reused |
| :---: | :--- | :--- | :--- |
| **Week 1** | **MCP Gateway & Token Optimizer** | Build `mcp_gateway.py` with Control Plane Tool Registry, Role-Scoped Access Policies, and DeepMind-style Response Field Projection. | `pipeline/neuralloop_books/models/` |
| **Week 2** | **Conversational Reading Co-Pilot** | Implement the Stage 2 in-situ co-pilot with quick action triggers (*"Show Me in Code"*, *"Production Reality Check"*), and margin whispers. | `pipeline/neuralloop_books/prompts.py`, `schemas.py` |
| **Week 3** | **Multi-Tier Memory & Socratic Recall** | Implement SQLite `learner_memory.db` and upgrade `recall.py` into a multi-turn Socratic diagnostic tutor with cross-document persistence. | `pipeline/neuralloop_books/recall.py` |
| **Week 4** | **Verification Sandbox & Harness** | Integrate the deterministic code execution sandbox and telemetry visualizer primitives into Stage 4. | `apple/Sources/NeuralLoopCore/` |

---

## 9. Success Metrics

1. **User Habit Retention:** $>40\%$ of users who start a book complete at least 5 chapter loops (vs. industry benchmark of $<10\%$ for technical book completion).
2. **Delayed Recall Accuracy:** $>85\%$ success rate on FSRS flashcard reviews at the 30-day interval.
3. **Misconception Resolution Rate:** $>75\%$ of flagged conceptual misunderstandings successfully resolved within subsequent recall sessions.
4. **Streaming Co-Pilot Latency:** $<400\text{ms}$ time-to-first-token on in-situ reading co-pilot queries via DeepMind KV cache alignment.
5. **Zero Cloud Ingestion Cost:** The entire system operates without recurring developer server bills by leveraging local compute and user-owned storage.
