# Mnemos Architecture: MCP Gateway & 5-Agent Pipeline
## Enterprise-Grade Agent Orchestration Inspired by Uber's MCP Management Platform

---

## 1. Executive Summary & Codebase Reality Audit

### 1.1 The Reality: 65% of Mnemos is Already Built and Working
Unlike conceptual whitepapers or greenfield prototypes, **65% of the Mnemos engine is already fully implemented, tested, and operational in this repository**. 

Before introducing new architectural extensions, we perform an explicit audit of what exists today versus the remaining 35% to be delivered:

```mermaid
flowchart LR
    subgraph ExistingCore ["Layer 1: Existing Built Core (65% COMPLETED)"]
        direction LR
        P1["PDF / EPUB Chapter Splitter<br>(chapters.py)"]
        P2["Multi-Lane Generation Pipeline<br>(pipeline.py, state.py)"]
        P3["LLM Engine Adapters<br>(Ollama, OpenAI, Claude, NotebookLM)"]
        P4["Deterministic FSRS-4.5 Scheduler<br>(FSRS.swift / Python Core)"]
        P5["Explainer Video Generator<br>(video.py - Chromium + PyAV)"]
        P6["5-Stage UI & Telemetry<br>(SwiftUI & Anti-Cheat Coverage)"]
        P7["Pip Sprite Animation Rig<br>(pip-rig.json, 8 poses, nudges)"]
    end

    subgraph NewArchitecture ["Layer 2: Architectural Extensions (35% TO BUILD)"]
        direction LR
        N1["Uber-Inspired MCP Gateway<br>(mcp_gateway.py: Proxy & Registry)"]
        N2["Shared Cognitive Learner Memory<br>(learner_memory.db: Misconceptions)"]
        N3["Windows Audio Synthesizer<br>(edge-tts + ffmpeg AAC encoder)"]
        N4["Conversational Socratic Recall<br>(Multi-turn probing tutor)"]
        N5["Android Companion App<br>(Podcast player + FSRS reviews)"]
    end

    ExistingCore --> NewArchitecture
```

### Detailed Component Implementation Audit

| Component | Status | Existing File Path in Repository | What Works Today | What This Architecture Adds |
| :--- | :---: | :--- | :--- | :--- |
| **Document Ingestion** | **DONE (90%)** | `pipeline/neuralloop_books/chapters.py` | Full PDF bookmarks, EPUB NCX/nav trees, section chunking, image extraction. | Document Intelligence Classifier (Research papers vs. slides). |
| **Generation Pipeline** | **DONE (85%)** | `pipeline/neuralloop_books/pipeline.py` | Multi-lane text & media execution, quota management, atomic `book.json` writes. | Dynamic stage re-routing via Orchestrator. |
| **Model Adapters** | **DONE (90%)** | `pipeline/neuralloop_books/models/` | Adapters for Ollama, OpenAI-compatible (LM Studio/OpenRouter), Anthropic, Hermes. | Unified MCP protocol abstraction. |
| **Spaced Repetition** | **DONE (95%)** | `apple/Sources/NeuralLoopCore/FSRS.swift` | Complete mathematical FSRS-4.5 scheduler (Stability, Difficulty, Retrievability). | Misconception-weighted card prioritization. |
| **Concept Knowledge Graph** | **DONE (85%)** | `pipeline/neuralloop_books/book_graph.py` | Inter-chapter concept linking, graph layouts, node dependencies. | Learner reconstruction puzzle mode. |
| **Video Generation** | **DONE (90%)** | `pipeline/neuralloop_books/video.py` | Headless Chromium frame-by-frame HTML animation rendered into MP4 via PyAV. | Preserved as-is. |
| **Pip Companion** | **DONE (90%)** | `design/pip/generate_pip.py`, `apple/App/` | 8 animated poses, procedural sprite layer system, gentle nudges, audio cues. | Home screen widget adaptation for Android. |
| **MCP Gateway** | **NEW (0%)** | `pipeline/neuralloop_books/gateway/` | *None (Agents call scripts directly).* | **Uber-inspired MCP Gateway:** Control Plane Registry + Data Plane Proxy Router. |
| **Learner Memory DB** | **NEW (10%)** | `apple/Sources/NeuralLoopCore/Progress.swift` | Basic step timestamps and card states in `progress.json`. | **Cognitive Memory:** Persistent SQLite tracking learner misconceptions across books. |
| **Windows Audio** | **ADAPT (40%)** | `pipeline/neuralloop_books/speech/rumik.py` | Script generator works; TTS is locked to Mac Apple Silicon `mlx_audio`. | Windows `edge-tts` multi-voice + FFmpeg normalization. |
| **Android Companion** | **NEW (0%)** | *New mobile directory* | iPad SwiftUI exists; no Android client exists. | Native/Flutter mobile app for commute audio & FSRS reviews. |

---

## 2. High-Level Design (HLD): The MCP Gateway Architecture (Left-to-Right)

In Uber Engineering's landmark platform architecture, [Designing MCP Gateway: Uber's MCP Management Platform](https://www.uber.com/us/en/blog/designing-mcp-gateway/), Uber decoupled agent logic from 10,000+ microservices using a centralized **Model Context Protocol (MCP) Gateway**.

Mnemos adapts this pattern to connect our **existing pipeline components** to the **5 specialized learning agents** without context window bloat or spaghetti code:

```mermaid
flowchart LR
    subgraph IngestionClient ["1. Client & Ingestion (ALREADY BUILT)"]
        direction LR
        RawDoc["PDF / EPUB"] --> Splitter["chapters.py Parser<br>[BUILT]"]
        Splitter --> DocClass["Doc Classifier<br>[NEW]"]
    end

    subgraph OrchestratorLayer ["2. Orchestration (UPGRADE)"]
        direction LR
        Orch["Learning Orchestrator<br>(State Machine & Stage Router)"]
    end

    subgraph Agents ["3. The 5 Specialized Learning Agents"]
        direction LR
        A1["1. Listen Agent<br>(Priming Script)"]
        A2["2. Read Agent<br>(Guided Plan)"]
        A3["3. Recall Agent<br>(Socratic Tutor)"]
        A4["4. Map Agent<br>(Graph Rebuild)"]
        A5["5. Remember Agent<br>(FSRS Cards)"]
    end

    subgraph MCPGateway ["4. Mnemos MCP Gateway (Uber-Inspired NEW LAYER)"]
        direction LR
        subgraph ControlPlane ["Control Plane (Registry & Governance)"]
            ToolReg["Tool & Schema Registry<br>(Metadata, Schemas)"]
            AccessPolicy["Access Control Matrix<br>(Discovery != Exposure)"]
        end
        subgraph DataPlane ["Data Plane (Proxy & Runtime Engine)"]
            Router["Proxy Router & Load Balancer"]
            Projector["Response Projection Engine<br>(Prunes Context Bloat)"]
            ProtocolTrans["Protocol Translation<br>(MCP JSON-RPC to Native)"]
        end
        ToolReg --> AccessPolicy
        AccessPolicy --> Router
        Router --> Projector
        Projector --> ProtocolTrans
    end

    subgraph Services ["5. Backend Services (65% BUILT / 35% EXTENSION)"]
        direction LR
        S_RAG["RAG Service<br>[SQLite FTS5 - NEW]"]
        S_Mem["Learner Memory DB<br>[SQLite - NEW]"]
        S_Audio["Audio Engine<br>[Edge-TTS + FFmpeg - NEW]"]
        S_FSRS["FSRS-4.5 Scheduler<br>[BUILT IN CORE]"]
        S_Graph["Knowledge Graph<br>[book_graph.py - BUILT]"]
        S_Models["Model Hub<br>[models/*.py - BUILT]"]
        S_Drive["Drive Sync Engine<br>[DriveStore - EXTEND]"]
    end

    %% Wiring
    DocClass --> Orch
    Orch <--> A1
    Orch <--> A2
    Orch <--> A3
    Orch <--> A4
    Orch <--> A5

    A1 --> Router
    A2 --> Router
    A3 --> Router
    A4 --> Router
    A5 --> Router

    ProtocolTrans <--> S_RAG
    ProtocolTrans <--> S_Mem
    ProtocolTrans <--> S_Audio
    ProtocolTrans <--> S_FSRS
    ProtocolTrans <--> S_Graph
    ProtocolTrans <--> S_Models
    ProtocolTrans <--> S_Drive
```

---

## 3. Core Architectural Pillars (Adapted from Uber's Gateway)

### 3.1 Control Plane vs. Data Plane Separation
* **Control Plane (Registry):** Maintains metadata for all tools. Registers input/output JSON schemas, parameter types, description embeddings, and service bindings without restarting agents or running processes.
* **Control Plane Governance ("Discovery $\neq$ Exposure"):** Newly registered tools are disabled by default. Each of the 5 agents is restricted strictly to its authorized tool set (e.g., the *Listen Agent* cannot invoke FSRS scheduling; the *Remember Agent* cannot call raw PDF splitters).
* **Data Plane (Proxy Router):** Routes standard MCP JSON-RPC requests (`tools/call`, `resources/read`) to native Python functions, SQLite queries, or system subprocesses with timeout and error handling.
* **Data Plane (Response Projection):** Solves LLM context window bloat. When an agent queries a 30-page chapter, the projector trims non-essential layout data and extracts only relevant semantic paragraphs.

---

### 3.2 Role-Scoped Tool Visibility Matrix

Instead of stuffing schemas for 20+ tools into every LLM prompt, the Gateway scopes tool discovery dynamically based on the active agent role:

```mermaid
flowchart LR
    Gateway["Mnemos MCP Gateway"]

    Gateway -->|"Scoped Tools"| A1["1. Listen Agent"]
    Gateway -->|"Scoped Tools"| A2["2. Read Agent"]
    Gateway -->|"Scoped Tools"| A3["3. Recall Agent"]
    Gateway -->|"Scoped Tools"| A4["4. Map Agent"]
    Gateway -->|"Scoped Tools"| A5["5. Remember Agent"]

    subgraph T_Listen ["Listen Agent Tools"]
        TL1["get_chapter_summary [BUILT]"]
        TL2["synth_multi_voice_dialogue [NEW]"]
        TL3["stitch_podcast_m4a [NEW]"]
    end

    subgraph T_Read ["Read Agent Tools"]
        TR1["get_section_tree [BUILT]"]
        TR2["read_chapter_chunk [BUILT]"]
        TR3["lookup_prerequisite_term [NEW]"]
    end

    subgraph T_Recall ["Recall Agent Tools"]
        TC1["query_book_ground_truth [NEW]"]
        TC2["get_learner_misconceptions [NEW]"]
        TC3["log_misconception_resolution [NEW]"]
    end

    subgraph T_Map ["Map Agent Tools"]
        TM1["extract_concept_nodes [BUILT]"]
        TM2["query_knowledge_graph [BUILT]"]
        TM3["generate_puzzle_edges [NEW]"]
    end

    subgraph T_Remember ["Remember Agent Tools"]
        TS1["get_due_fsrs_cards [BUILT]"]
        TS2["schedule_card_review [BUILT]"]
        TS3["create_atomic_card [BUILT]"]
    end

    A1 -.-> T_Listen
    A2 -.-> T_Read
    A3 -.-> T_Recall
    A4 -.-> T_Map
    A5 -.-> T_Remember
```

---

## 4. Low-Level Design (LLD): The MCP Gateway Engine

### 4.1 Component Breakdown & Data Flow (Left-to-Right)

```mermaid
flowchart LR
    Agent["Active Agent<br>(e.g. Recall Agent)"] --> Request["MCP JSON-RPC Request<br>method: 'tools/call'<br>params: {name: 'query_ground_truth'}"]
    
    subgraph GatewayCore ["MCP Gateway Core"]
        direction LR
        AuthCheck{"Policy & Scope<br>Validator"}
        CacheCheck{"Semantic Response<br>Cache"}
        Dispatcher["Driver Dispatcher"]
        Projector["Response Field<br>Projector"]
    end

    Request --> AuthCheck
    AuthCheck -->|"Approved"| CacheCheck
    AuthCheck -->|"Forbidden"| DeniedErr["Error: 403 Forbidden"]
    
    CacheCheck -->|"Cache Hit"| ReturnCached["Return Cached JSON-RPC"]
    CacheCheck -->|"Cache Miss"| Dispatcher
    
    Dispatcher --> NativeDriver["Native Service Driver<br>(FTS5 / Audio / FSRS)"]
    NativeDriver --> RawResult["Raw System Payload"]
    RawResult --> Projector
    Projector --> CleanResponse["Projected JSON-RPC Result"]
    CleanResponse --> Agent
```

---

### 4.2 Python Implementation Specification: `mcp_gateway.py`

This module connects directly to the existing `pipeline/neuralloop_books/` package:

```python
"""
Mnemos MCP Gateway Core.
Inspired by Uber's MCP Management Platform (Control Plane / Data Plane separation).
Integrates with existing pipeline modules (chapters.py, book_graph.py, models/).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Coroutine
import logging

logger = logging.getLogger("mnemos.mcp_gateway")

class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    LISTEN = "listen_agent"
    READ = "read_agent"
    RECALL = "recall_agent"
    MAP = "map_agent"
    REMEMBER = "remember_agent"

@dataclass
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    allowed_roles: set[AgentRole]
    handler: Callable[..., Coroutine[Any, Any, dict[str, Any]]]
    enabled: bool = True
    projection_fields: list[str] | None = None

class MCPGateway:
    """Central MCP Gateway handling Tool Discovery, Scoped Access, and Protocol Routing."""

    def __init__(self):
        self._registry: dict[str, MCPToolDefinition] = {}
        self._cache: dict[str, dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        allowed_roles: set[AgentRole],
        handler: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
        projection_fields: list[str] | None = None,
    ):
        """Register a backend service tool into the Control Plane Registry."""
        self._registry[name] = MCPToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            allowed_roles=allowed_roles,
            handler=handler,
            enabled=True,
            projection_fields=projection_fields,
        )
        logger.info(f"Registered tool '{name}' authorized for: {[r.value for r in allowed_roles]}")

    def get_scoped_tools(self, role: AgentRole) -> list[dict[str, Any]]:
        """
        Incremental Discovery: Returns ONLY tool schemas authorized for the active agent.
        Eliminates prompt context window bloat.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._registry.values()
            if tool.enabled and role in tool.allowed_roles
        ]

    async def invoke_tool(
        self,
        caller_role: AgentRole,
        tool_name: str,
        arguments: dict[str, Any],
        projection: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Data Plane Execution Router:
        1. Validates access permissions (Discovery != Exposure).
        2. Executes native backend driver.
        3. Projects response to prevent LLM context bloat.
        """
        tool = self._registry.get(tool_name)
        if not tool or not tool.enabled:
            raise ValueError(f"Tool '{tool_name}' not found or currently disabled.")

        # Governance Check: Explicit permission per agent role
        if caller_role not in tool.allowed_roles:
            logger.error(f"Security Alert: {caller_role.value} denied access to {tool_name}")
            raise PermissionError(f"Agent '{caller_role.value}' is not authorized to invoke '{tool_name}'.")

        # Execute Backend Handler
        try:
            raw_output = await tool.handler(**arguments)
        except Exception as e:
            logger.exception(f"Execution error invoking {tool_name}: {e}")
            return {"error": str(e), "status": "failed"}

        # Response Projection: Strip non-essential fields before context ingestion
        fields_to_project = projection or tool.projection_fields
        if fields_to_project and isinstance(raw_output, dict):
            projected = {k: raw_output[k] for k in fields_to_project if k in raw_output}
            return {"status": "success", "data": projected}

        return {"status": "success", "data": raw_output}
```

---

## 5. End-to-End Execution Flow (Left-to-Right Sequence)

The following sequence diagram demonstrates an active Socratic Recall check executed through the MCP Gateway, combining our **existing pipeline text** with the **new Cognitive Memory layer**:

```mermaid
sequenceDiagram
    autonumber
    actor Learner
    participant WinUI as Windows App UI
    participant Orch as Learning Orchestrator
    participant RecallAg as Recall Agent
    participant Gateway as Mnemos MCP Gateway
    participant RAG as Document RAG Service
    participant Memory as Learner Memory Service

    Learner->>WinUI: Submits explanation of "Raft Log Compaction"
    WinUI->>Orch: on_user_recall_submitted(text)
    Orch->>RecallAg: evaluate_understanding(user_text, chapter_id=4)
    
    Note over RecallAg, Gateway: Incremental Discovery & Scoped Call
    RecallAg->>Gateway: invoke_tool(role="recall_agent", name="query_book_ground_truth", args={chapter: 4, query: user_text})
    Gateway->>Gateway: Verify RecallAgent in allowed_roles
    Gateway->>RAG: search_fts5_and_embeddings(chapter=4, query=user_text)
    RAG-->>Gateway: Raw document chunks & metadata (45 KB)
    Gateway->>Gateway: Project response (top 3 claims, 1.2 KB)
    Gateway-->>RecallAg: Projected Ground Truth Context

    RecallAg->>Gateway: invoke_tool(role="recall_agent", name="get_learner_misconceptions", args={domain: "distributed_systems"})
    Gateway->>Memory: fetch_active_misconceptions(domain)
    Memory-->>Gateway: [{"concept": "snapshot_isolation", "weakness": "..."}]
    Gateway-->>RecallAg: Filtered Learner Cognitive Profile

    Note over RecallAg: LLM Diagnostic Execution (Dual Memory + Ground Truth)
    RecallAg->>RecallAg: Detects subtle snapshot ordering confusion
    RecallAg-->>Orch: Result: status="needs_refinement", socratic_prompt="..."
    Orch->>WinUI: Displays Pip's Socratic Question
```

---

## 6. Backend Tool Services: Linking Built Core to New Extensions

```mermaid
flowchart LR
    Gateway["Mnemos MCP Gateway Router"]

    subgraph BuiltServices ["Already Built in Codebase (Reused As-Is)"]
        direction LR
        S_Split["chapters.py<br>(TOC & Section Chunker)"]
        S_Graph["book_graph.py<br>(Knowledge Graph Builder)"]
        S_FSRS["FSRS-4.5 Engine<br>(Deterministic Math)"]
        S_Models["models/*.py<br>(Ollama, OpenAI, Claude)"]
    end

    subgraph NewServices ["New Extensions (To Complete)"]
        direction LR
        S_RAG["RAG Service<br>(SQLite FTS5 + BM25)"]
        S_Mem["Learner Memory Service<br>(learner_memory.db)"]
        S_Audio["Windows Audio Service<br>(Edge-TTS + FFmpeg)"]
        S_Sync["Drive Sync Service<br>(Python DriveStore)"]
    end

    Gateway <--> BuiltServices
    Gateway <--> NewServices
```

---

## 7. Execution Plan to Complete the Remaining 35%

| Phase | Milestone | Existing Baseline in Repo | Work to Complete |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Windows Audio Engine** | `audio.py` + `local.py` (Script works; TTS is Mac MLX). | Implement `speech/windows_tts.py` with `edge-tts` + `ffmpeg`. |
| **Phase 2** | **MCP Gateway Core** | Tools called directly in pipeline scripts. | Implement `mcp_gateway.py` with Registry and Role Scoping. |
| **Phase 3** | **Shared Learner Memory** | `progress.json` tracks timestamps only. | Create SQLite `learner_memory.db` tracking misconceptions across books. |
| **Phase 4** | **Conversational Socratic Recall** | `recall.py` has single-turn word/LLM grading. | Upgrade prompt and state machine to multi-turn Socratic probing. |
| **Phase 5** | **Android Companion MVP** | iPad SwiftUI app in `apple/`. | Build Flutter/Kotlin mobile client for audio playback & FSRS review. |
