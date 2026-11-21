-- =============================================================================
-- Mnemos — Initial PostgreSQL Schema
-- Migration: 001_initial_schema.sql
-- Architecture Reference: architecture.md (HLD + LLD sections 5–10)
--
-- Covers every entity defined in the Multi-Tier Cognitive Memory Engine (§8/§6),
-- the MCP Gateway Control Plane (§5), the Verification Sandbox (§9/§7),
-- the 5-Stage Learning Loop, and all supporting lookup / audit tables.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Housekeeping: extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- trigram indexes for FTS
CREATE EXTENSION IF NOT EXISTS "vector";        -- pgvector for embeddings
                                                -- (install pgvector separately
                                                --  if not available; harmless
                                                --  to comment out for dev)

-- ---------------------------------------------------------------------------
-- Helper: updated_at trigger function (reused on every mutable table)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- SECTION 1 — LEARNER IDENTITY
-- Source: architecture.md §8 (LEARNER_PROFILE entity)
-- =============================================================================

CREATE TABLE learner_profiles (
    -- Identity
    user_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT        NOT NULL UNIQUE,
    display_name        TEXT        NOT NULL,

    -- Learning preferences (from plan.md §6 LLD)
    preferred_language  TEXT        NOT NULL DEFAULT 'python',   -- default code-example language
    preferred_style     TEXT        NOT NULL DEFAULT 'visual',   -- 'visual' | 'textual' | 'mixed'

    -- Retention config
    retention_target    FLOAT       NOT NULL DEFAULT 0.90        -- FSRS target retrievability (90%)
                                    CHECK (retention_target BETWEEN 0.5 AND 1.0),
    global_retention_score FLOAT   NOT NULL DEFAULT 0.0
                                    CHECK (global_retention_score BETWEEN 0.0 AND 1.0),

    -- Sync / device metadata
    last_synced_at      TIMESTAMPTZ,
    device_ids          TEXT[]      NOT NULL DEFAULT '{}',       -- array of device fingerprints

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_learner_profiles_updated_at
    BEFORE UPDATE ON learner_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- SECTION 2 — DOCUMENT LIBRARY
-- Source: Mnemo/docs/ARCHITECTURE.md "book.json" contract; pipeline/ modules
-- =============================================================================

CREATE TABLE books (
    book_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id            UUID        NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,

    -- Bibliographic metadata
    title               TEXT        NOT NULL,
    author              TEXT,
    source_format       TEXT        NOT NULL CHECK (source_format IN ('pdf', 'epub')),
    source_sha256       TEXT,                                    -- hash of original file

    -- Pipeline state (mirrors pipeline/neuralloop_books/state.py)
    pipeline_status     TEXT        NOT NULL DEFAULT 'queued'
                                    CHECK (pipeline_status IN (
                                        'queued', 'running', 'done',
                                        'failed', 'interrupted'
                                    )),
    total_chapters      INT         NOT NULL DEFAULT 0,
    prepared_chapters   INT         NOT NULL DEFAULT 0,

    -- Storage
    storage_path        TEXT        NOT NULL,                   -- relative path inside app support dir
    drive_folder_id     TEXT,                                   -- Google Drive appdata folder id

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_books_owner ON books(owner_id);

CREATE TRIGGER trg_books_updated_at
    BEFORE UPDATE ON books
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ---------------------------------------------------------------------------
-- Chapters — one row per parsed chapter (chapters.py output)
-- ---------------------------------------------------------------------------
CREATE TABLE chapters (
    chapter_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id             UUID        NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,

    chapter_index       INT         NOT NULL,                   -- 1-based, matches chapters/01.md
    title               TEXT        NOT NULL,
    markdown_path       TEXT        NOT NULL,                   -- relative path to chapters/NN.md
    word_count          INT         NOT NULL DEFAULT 0,

    -- Pipeline item readiness (mirrors bookdata.py item statuses)
    prime_ready         BOOLEAN     NOT NULL DEFAULT FALSE,
    copilot_ready       BOOLEAN     NOT NULL DEFAULT FALSE,
    socratic_ready      BOOLEAN     NOT NULL DEFAULT FALSE,
    harness_ready       BOOLEAN     NOT NULL DEFAULT FALSE,
    cards_ready         BOOLEAN     NOT NULL DEFAULT FALSE,

    -- Ordering invariant
    UNIQUE (book_id, chapter_index)
);

CREATE INDEX idx_chapters_book ON chapters(book_id);


-- =============================================================================
-- SECTION 3 — 5-STAGE MASTERY LOOP STATE
-- Source: architecture.md §4 (Modernized 5-Stage Cognitive Pipeline)
--         Mnemo/apple/Sources/NeuralLoopCore/Loop.swift
-- =============================================================================

CREATE TYPE loop_stage AS ENUM (
    'prime',       -- Stage 1: Architectural briefing & dialogue
    'read',        -- Stage 2: Conversational active reading
    'recall',      -- Stage 3: Socratic retrieval practice
    'harness',     -- Stage 4: Interactive verification sandbox
    'remember'     -- Stage 5: FSRS spaced-repetition review
);

CREATE TYPE loop_status AS ENUM (
    'locked',      -- chapter N is blocked until N-1 loop is closed
    'unlocked',    -- available to start
    'in_progress', -- learner has started at least one stage
    'closed'       -- all 5 stages completed; next chapter unlocks
);

CREATE TABLE chapter_loops (
    loop_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id          UUID        NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    chapter_id          UUID        NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,

    status              loop_status NOT NULL DEFAULT 'locked',
    active_stage        loop_stage,

    -- Per-stage completion timestamps
    prime_completed_at   TIMESTAMPTZ,
    read_completed_at    TIMESTAMPTZ,
    recall_completed_at  TIMESTAMPTZ,
    harness_completed_at TIMESTAMPTZ,
    remember_completed_at TIMESTAMPTZ,
    closed_at            TIMESTAMPTZ,

    -- Reading telemetry (ReadingCredit.swift equivalent)
    total_read_seconds   INT         NOT NULL DEFAULT 0,
    scroll_depth_pct     FLOAT       NOT NULL DEFAULT 0.0
                                     CHECK (scroll_depth_pct BETWEEN 0.0 AND 1.0),

    UNIQUE (learner_id, chapter_id),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chapter_loops_learner ON chapter_loops(learner_id);
CREATE INDEX idx_chapter_loops_chapter ON chapter_loops(chapter_id);

CREATE TRIGGER trg_chapter_loops_updated_at
    BEFORE UPDATE ON chapter_loops
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- SECTION 4 — KNOWLEDGE GRAPH (Semantic Memory Layer)
-- Source: architecture.md §8 (Semantic Knowledge Graph / book_graph.py)
--         plan.md §6 (Semantic Memory — M_Sem)
-- =============================================================================

CREATE TABLE concept_nodes (
    concept_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id             UUID        NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    chapter_id          UUID        REFERENCES chapters(chapter_id) ON DELETE SET NULL,

    canonical_name      TEXT        NOT NULL,
    domain              TEXT        NOT NULL DEFAULT 'general',  -- e.g. 'distributed-systems'
    description         TEXT,

    -- Vector embedding for semantic search (pgvector)
    -- Dimension 384 matches all-MiniLM-L6-v2 / bge-small-en-v1.5 (left.md §3.4)
    embedding           vector(384),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_concept_nodes_book ON concept_nodes(book_id);
CREATE INDEX idx_concept_nodes_embedding ON concept_nodes USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Directed prerequisite edges: source must be mastered before target
CREATE TABLE concept_edges (
    edge_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_concept_id   UUID        NOT NULL REFERENCES concept_nodes(concept_id) ON DELETE CASCADE,
    target_concept_id   UUID        NOT NULL REFERENCES concept_nodes(concept_id) ON DELETE CASCADE,
    edge_type           TEXT        NOT NULL DEFAULT 'prerequisite'
                                    CHECK (edge_type IN ('prerequisite', 'related', 'extends', 'contradicts')),
    weight              FLOAT       NOT NULL DEFAULT 1.0,

    UNIQUE (source_concept_id, target_concept_id, edge_type)
);

CREATE INDEX idx_concept_edges_source ON concept_edges(source_concept_id);
CREATE INDEX idx_concept_edges_target ON concept_edges(target_concept_id);


-- =============================================================================
-- SECTION 5 — CONCEPT MASTERY (Semantic Memory — per learner×concept)
-- Source: architecture.md §8 CONCEPT_MASTERY entity (both erDiagrams)
-- =============================================================================

CREATE TABLE concept_mastery (
    mastery_id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id              UUID        NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    concept_id              UUID        NOT NULL REFERENCES concept_nodes(concept_id) ON DELETE CASCADE,

    mastery_score           FLOAT       NOT NULL DEFAULT 0.0
                                        CHECK (mastery_score BETWEEN 0.0 AND 1.0),
    total_recall_attempts   INT         NOT NULL DEFAULT 0,
    failed_recall_attempts  INT         NOT NULL DEFAULT 0,
    last_tested_at          TIMESTAMPTZ,

    UNIQUE (learner_id, concept_id),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_concept_mastery_learner ON concept_mastery(learner_id);

CREATE TRIGGER trg_concept_mastery_updated_at
    BEFORE UPDATE ON concept_mastery
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- SECTION 6 — MISCONCEPTIONS (Semantic Memory — diagnostic layer)
-- Source: architecture.md §8 MISCONCEPTIONS entity; plan.md §6 M_Sem
--         left.md §5 Socratic Diagnostic Agent
-- =============================================================================

CREATE TABLE misconceptions (
    misconception_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id              UUID        NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    concept_id              UUID        NOT NULL REFERENCES concept_nodes(concept_id) ON DELETE CASCADE,

    -- Diagnostic fields (from architecture.md §8)
    fallacy_category        TEXT,                               -- e.g. 'conflation', 'false-causality'
    diagnosis_summary       TEXT        NOT NULL,
    triggering_pattern      TEXT,                               -- exact student phrase that exposed it
    socratic_probe          TEXT,                               -- targeted follow-up question posed

    -- Resolution tracking
    resolved                BOOLEAN     NOT NULL DEFAULT FALSE,
    resolved_at             TIMESTAMPTZ,

    -- Source recall session
    source_recall_id        UUID,                               -- FK set after recall_sessions exists

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_misconceptions_learner  ON misconceptions(learner_id);
CREATE INDEX idx_misconceptions_concept  ON misconceptions(concept_id);
CREATE INDEX idx_misconceptions_unresolved ON misconceptions(learner_id) WHERE NOT resolved;

CREATE TRIGGER trg_misconceptions_updated_at
    BEFORE UPDATE ON misconceptions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- SECTION 7 — EPISODIC MEMORY
-- Source: architecture.md §8 EPISODIC_LOG entity; plan.md §6 M_Epi
--         left.md §3.1 Episodic Memory Store
-- =============================================================================

CREATE TYPE episodic_stage AS ENUM (
    'prime', 'read', 'recall', 'harness', 'remember'
);

CREATE TABLE episodic_log (
    log_id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id              UUID            NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    chapter_id              UUID            REFERENCES chapters(chapter_id) ON DELETE SET NULL,

    stage                   episodic_stage  NOT NULL,
    event_type              TEXT            NOT NULL,           -- 'assertion_failure' | 'confusion_flag' | 'misconception' | 'timeout'
    simulation_id           UUID,                              -- FK to sandbox_runs if stage='harness'

    failure_mode_observed   TEXT,                              -- freetext: e.g. 'split-brain on partition'
    agent_diagnosis         TEXT,                              -- agent's textual diagnosis

    -- Time-decay relevance (left.md §3.1 "exponential time-decay relevance scoring")
    temporal_decay_weight   FLOAT           NOT NULL DEFAULT 1.0
                                            CHECK (temporal_decay_weight BETWEEN 0.0 AND 1.0),
    decayed_at              TIMESTAMPTZ,                       -- when the weight was last recalculated

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_episodic_log_learner  ON episodic_log(learner_id);
CREATE INDEX idx_episodic_log_chapter  ON episodic_log(chapter_id);
CREATE INDEX idx_episodic_log_stage    ON episodic_log(stage);
-- Recency-biased index for memory retrieval queries
CREATE INDEX idx_episodic_log_recent   ON episodic_log(learner_id, created_at DESC);


-- =============================================================================
-- SECTION 8 — RECALL SESSIONS (Stage 3 — Socratic Recall)
-- Source: architecture.md §8 RECALL_SESSIONS entity; plan.md §6 M_Sem
--         left.md §5 Socratic Diagnostic Agent
-- =============================================================================

CREATE TABLE recall_sessions (
    session_id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id              UUID        NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    chapter_id              UUID        NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    loop_id                 UUID        REFERENCES chapter_loops(loop_id) ON DELETE SET NULL,

    -- Prompt & response (from architecture.md plan.md RECALL_SESSIONS)
    prompt_text             TEXT        NOT NULL,
    user_response           TEXT        NOT NULL,
    awarded_score           FLOAT       NOT NULL DEFAULT 0.0
                                        CHECK (awarded_score BETWEEN 0.0 AND 1.0),

    -- Scoring breakdown (left.md §5.1 Semantic Rubric Grader)
    score_core_principle    FLOAT       CHECK (score_core_principle BETWEEN 0.0 AND 1.0),
    score_invariants        FLOAT       CHECK (score_invariants BETWEEN 0.0 AND 1.0),
    score_tradeoffs         FLOAT       CHECK (score_tradeoffs BETWEEN 0.0 AND 1.0),

    socratic_feedback       TEXT,                               -- agent's returned question / feedback
    agent_role              TEXT        NOT NULL DEFAULT 'socratic_recall',

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_recall_sessions_learner  ON recall_sessions(learner_id);
CREATE INDEX idx_recall_sessions_chapter  ON recall_sessions(chapter_id);

-- Back-fill FK from misconceptions → recall_sessions
ALTER TABLE misconceptions
    ADD CONSTRAINT fk_misconceptions_recall
    FOREIGN KEY (source_recall_id) REFERENCES recall_sessions(session_id) ON DELETE SET NULL;


-- =============================================================================
-- SECTION 9 — FSRS FLASHCARDS (Stage 5 — Remember)
-- Source: architecture.md §8 FSRS_CARDS entity (both erDiagrams)
--         Mnemo/apple/Sources/NeuralLoopCore/FSRS.swift
-- =============================================================================

-- FSRS-4.5 learning states (mirrors FSRS.swift State enum)
CREATE TYPE fsrs_state AS ENUM (
    'new',          -- card never reviewed
    'learning',     -- in initial learning phase
    'review',       -- graduated to review phase
    'relearning'    -- lapsed; re-entering learning
);

CREATE TABLE fsrs_cards (
    card_id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id              UUID        NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    concept_id              UUID        REFERENCES concept_nodes(concept_id) ON DELETE SET NULL,
    chapter_id              UUID        REFERENCES chapters(chapter_id) ON DELETE SET NULL,

    -- Card content
    front                   TEXT        NOT NULL,
    back                    TEXT        NOT NULL,
    tags                    TEXT[]      NOT NULL DEFAULT '{}',

    -- FSRS-4.5 state variables (architecture.md §8 FSRS_CARDS)
    stability               FLOAT       NOT NULL DEFAULT 0.0,       -- S: days before 90% forgetting
    difficulty              FLOAT       NOT NULL DEFAULT 5.0        -- D: [1..10]
                                        CHECK (difficulty BETWEEN 1.0 AND 10.0),
    reps                    INT         NOT NULL DEFAULT 0,
    lapses                  INT         NOT NULL DEFAULT 0,
    current_state           fsrs_state  NOT NULL DEFAULT 'new',
    due_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_reviewed_at        TIMESTAMPTZ,

    -- Misconception linkage (cards derived from diagnosed misunderstandings)
    source_misconception_id UUID        REFERENCES misconceptions(misconception_id) ON DELETE SET NULL,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_fsrs_cards_learner  ON fsrs_cards(learner_id);
CREATE INDEX idx_fsrs_cards_due      ON fsrs_cards(learner_id, due_at)
    WHERE current_state != 'new';

CREATE TRIGGER trg_fsrs_cards_updated_at
    BEFORE UPDATE ON fsrs_cards
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- Review event log (immutable; never updated — append-only audit trail)
CREATE TABLE fsrs_reviews (
    review_id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id                 UUID        NOT NULL REFERENCES fsrs_cards(card_id) ON DELETE CASCADE,
    learner_id              UUID        NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,

    -- Rating: 1=Again 2=Hard 3=Good 4=Easy  (FSRS-4.5 scale)
    rating                  SMALLINT    NOT NULL CHECK (rating BETWEEN 1 AND 4),

    -- Snapshot of card state BEFORE this review (for replay / debugging)
    pre_stability           FLOAT       NOT NULL,
    pre_difficulty          FLOAT       NOT NULL,
    pre_state               fsrs_state  NOT NULL,

    -- Snapshot AFTER
    post_stability          FLOAT       NOT NULL,
    post_difficulty         FLOAT       NOT NULL,
    post_state              fsrs_state  NOT NULL,
    next_due_at             TIMESTAMPTZ NOT NULL,

    -- Timing
    response_ms             INT,                                -- how long the learner took to answer
    reviewed_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_fsrs_reviews_card    ON fsrs_reviews(card_id);
CREATE INDEX idx_fsrs_reviews_learner ON fsrs_reviews(learner_id, reviewed_at DESC);


-- =============================================================================
-- SECTION 10 — MCP GATEWAY CONTROL PLANE
-- Source: architecture.md §5 (Uber MCP Gateway)
--         architecture.md §5.2 Scoped Tools Matrix
--         left.md §1 Uber-Inspired MCP Gateway
-- =============================================================================

CREATE TYPE agent_role AS ENUM (
    'orchestrator',
    'prime_agent',
    'read_copilot',
    'socratic_recall',
    'challenge_orchestrator',
    'remember_agent'
);

-- Tool registry (Control Plane) — mirrors MCPToolDefinition dataclass in architecture.md §10
CREATE TABLE mcp_tools (
    tool_id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    TEXT        NOT NULL UNIQUE,
    description             TEXT        NOT NULL,

    -- JSON Schema for the tool's input (stored as jsonb for query flexibility)
    input_schema            JSONB       NOT NULL DEFAULT '{}',

    -- Semantic tags for intent-based capability discovery (left.md §1.1)
    stage_tags              TEXT[]      NOT NULL DEFAULT '{}',   -- e.g. '{stage:read, stage:recall}'
    allowed_roles           agent_role[] NOT NULL DEFAULT '{}',

    -- Response projection: list of output fields to return to the calling agent
    -- (DeepMind field projection — architecture.md §6)
    projection_fields       TEXT[],

    -- Token budget for this tool's schema definition
    schema_token_budget     INT         NOT NULL DEFAULT 600,

    enabled                 BOOLEAN     NOT NULL DEFAULT TRUE,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_mcp_tools_enabled ON mcp_tools(enabled) WHERE enabled;

CREATE TRIGGER trg_mcp_tools_updated_at
    BEFORE UPDATE ON mcp_tools
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- Tool invocation audit log (Data Plane — immutable)
CREATE TABLE mcp_invocations (
    invocation_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id                 UUID        NOT NULL REFERENCES mcp_tools(tool_id),
    learner_id              UUID        REFERENCES learner_profiles(user_id) ON DELETE SET NULL,
    caller_role             agent_role  NOT NULL,

    -- Request / response payloads (DeepMind projected output stored separately)
    arguments               JSONB       NOT NULL DEFAULT '{}',
    projected_output        JSONB,
    raw_output_size_bytes   INT,
    projected_size_bytes    INT,

    -- Circuit breaker state at time of call
    circuit_state           TEXT        NOT NULL DEFAULT 'closed'
                                        CHECK (circuit_state IN ('closed', 'open', 'half_open')),

    status                  TEXT        NOT NULL DEFAULT 'success'
                                        CHECK (status IN ('success', 'failed', 'unauthorized', 'timeout')),
    error_message           TEXT,
    duration_ms             INT,

    invoked_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_mcp_invocations_tool    ON mcp_invocations(tool_id);
CREATE INDEX idx_mcp_invocations_learner ON mcp_invocations(learner_id);
CREATE INDEX idx_mcp_invocations_status  ON mcp_invocations(status) WHERE status != 'success';


-- Circuit-breaker state table (one row per tool — upserted by the gateway)
CREATE TABLE mcp_circuit_breakers (
    tool_id                 UUID        PRIMARY KEY REFERENCES mcp_tools(tool_id) ON DELETE CASCADE,
    state                   TEXT        NOT NULL DEFAULT 'closed'
                                        CHECK (state IN ('closed', 'open', 'half_open')),
    failure_count           INT         NOT NULL DEFAULT 0,
    success_count           INT         NOT NULL DEFAULT 0,
    last_failure_at         TIMESTAMPTZ,
    opened_at               TIMESTAMPTZ,
    half_open_at            TIMESTAMPTZ,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_circuit_breakers_updated_at
    BEFORE UPDATE ON mcp_circuit_breakers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- SECTION 11 — VERIFICATION SANDBOX (Stage 4 — Harness)
-- Source: architecture.md §9 (Verification Sandbox & Virtual Shims)
--         plan.md §7 (Interactive Verification Sandbox)
--         left.md §6 Interactive Verification Sandbox
-- =============================================================================

-- Pre-defined challenge scenarios (architecture.md §9: Challenge Matrix)
CREATE TABLE sandbox_challenges (
    challenge_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id                 UUID        REFERENCES books(book_id) ON DELETE SET NULL,
    chapter_id              UUID        REFERENCES chapters(chapter_id) ON DELETE SET NULL,

    title                   TEXT        NOT NULL,
    description             TEXT        NOT NULL,
    difficulty              TEXT        NOT NULL DEFAULT 'medium'
                                        CHECK (difficulty IN ('easy', 'medium', 'hard')),

    -- Domain of the challenge (e.g. 'idempotency', 'split-brain', 'lru-cache')
    domain_tags             TEXT[]      NOT NULL DEFAULT '{}',

    -- Initial simulation parameters (JSON, consumed by the FSM)
    initial_params          JSONB       NOT NULL DEFAULT '{}',
                                        -- e.g. {"failure_rate": 0.15, "latency_ms": 120, "packet_loss": 0.05}

    -- Grading / success criteria
    success_criteria        JSONB       NOT NULL DEFAULT '{}',

    -- Virtual shims required for this challenge
    requires_virtual_clock  BOOLEAN     NOT NULL DEFAULT FALSE,
    requires_virtual_storage BOOLEAN    NOT NULL DEFAULT FALSE,
    requires_virtual_network BOOLEAN    NOT NULL DEFAULT FALSE,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sandbox_challenges_chapter ON sandbox_challenges(chapter_id);

CREATE TRIGGER trg_sandbox_challenges_updated_at
    BEFORE UPDATE ON sandbox_challenges
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- Individual sandbox run (each learner attempt)
CREATE TABLE sandbox_runs (
    run_id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id              UUID        NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    challenge_id            UUID        NOT NULL REFERENCES sandbox_challenges(challenge_id),
    loop_id                 UUID        REFERENCES chapter_loops(loop_id) ON DELETE SET NULL,

    -- Submitted code
    submitted_code          TEXT        NOT NULL,
    language                TEXT        NOT NULL DEFAULT 'python'
                                        CHECK (language IN ('python', 'go', 'typescript', 'rust')),

    -- Execution outcome (left.md §6.1 Sandbox Runner)
    outcome                 TEXT        NOT NULL DEFAULT 'pending'
                                        CHECK (outcome IN ('pending', 'pass', 'fail', 'timeout', 'error')),
    stdout                  TEXT,
    stderr                  TEXT,
    execution_ms            INT,
    peak_memory_kb          INT,

    -- Fault injections applied during this run
    fault_config            JSONB       NOT NULL DEFAULT '{}',
                                        -- e.g. {"clock_advance_ms": 5000, "packet_drop_rate": 0.3}

    -- Test matrix results (per-test pass/fail JSON)
    test_results            JSONB       NOT NULL DEFAULT '[]',

    -- Simulation trace frames (for SwiftUI replay)
    trace_frames            JSONB       NOT NULL DEFAULT '[]',

    started_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at            TIMESTAMPTZ
);

CREATE INDEX idx_sandbox_runs_learner    ON sandbox_runs(learner_id);
CREATE INDEX idx_sandbox_runs_challenge  ON sandbox_runs(challenge_id);
CREATE INDEX idx_sandbox_runs_outcome    ON sandbox_runs(outcome);

-- Back-fill FK from episodic_log → sandbox_runs
ALTER TABLE episodic_log
    ADD CONSTRAINT fk_episodic_simulation
    FOREIGN KEY (simulation_id) REFERENCES sandbox_runs(run_id) ON DELETE SET NULL;


-- =============================================================================
-- SECTION 12 — ACTIVE READING CO-PILOT (Stage 2)
-- Source: architecture.md §7 (Conversational Active Reading)
--         plan.md §4.2 Stage 2; left.md §4
-- =============================================================================

CREATE TYPE copilot_action AS ENUM (
    'show_in_code',          -- "Show Me in Code"
    'production_reality',    -- "Production Reality Check"
    'devils_advocate',       -- "Devil's Advocate & Trade-Offs"
    'spin_up_sandbox',       -- "Spin Up Inline Sandbox"
    'margin_whisper',        -- Proactive Socratic margin note
    'freeform'               -- open-ended question
);

CREATE TABLE copilot_interactions (
    interaction_id          UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id              UUID            NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    chapter_id              UUID            NOT NULL REFERENCES chapters(chapter_id) ON DELETE CASCADE,
    loop_id                 UUID            REFERENCES chapter_loops(loop_id) ON DELETE SET NULL,

    action_type             copilot_action  NOT NULL,

    -- Context sent to the agent
    selected_paragraph      TEXT,
    scroll_position_pct     FLOAT           CHECK (scroll_position_pct BETWEEN 0.0 AND 1.0),
    user_query              TEXT,

    -- Agent response
    agent_response          TEXT,
    code_snippet            TEXT,           -- populated for 'show_in_code'
    code_language           TEXT,
    response_latency_ms     INT,            -- target <400ms (plan.md §9)

    -- Token optimization metrics (DeepMind optimizer)
    tokens_in               INT,
    tokens_out              INT,
    prompt_cache_hit        BOOLEAN         NOT NULL DEFAULT FALSE,

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_copilot_interactions_learner  ON copilot_interactions(learner_id);
CREATE INDEX idx_copilot_interactions_chapter  ON copilot_interactions(chapter_id);


-- =============================================================================
-- SECTION 13 — PROCEDURAL MEMORY (Debugging Blueprints)
-- Source: architecture.md §8 (Procedural Memory — M_Pro)
--         left.md §3.3 Procedural Memory Engine
-- =============================================================================

CREATE TABLE procedural_templates (
    template_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    title                   TEXT        NOT NULL,
    description             TEXT        NOT NULL,
    domain_tags             TEXT[]      NOT NULL DEFAULT '{}',

    -- Structured steps (JSON array of {step, rationale, code?})
    steps                   JSONB       NOT NULL DEFAULT '[]',

    -- Reuse tracking (how often this blueprint was surfaced)
    use_count               INT         NOT NULL DEFAULT 0,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_procedural_templates_updated_at
    BEFORE UPDATE ON procedural_templates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- Linking table: which templates are relevant for a given misconception
CREATE TABLE misconception_templates (
    misconception_id        UUID        NOT NULL REFERENCES misconceptions(misconception_id) ON DELETE CASCADE,
    template_id             UUID        NOT NULL REFERENCES procedural_templates(template_id) ON DELETE CASCADE,
    relevance_score         FLOAT       NOT NULL DEFAULT 1.0,
    PRIMARY KEY (misconception_id, template_id)
);


-- =============================================================================
-- SECTION 14 — TOKEN OPTIMIZATION AUDIT
-- Source: architecture.md §6 (DeepMind Token Optimization)
--         left.md §2 Google DeepMind Token Optimization Engine
-- =============================================================================

CREATE TABLE token_optimization_log (
    log_id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    invocation_id           UUID        REFERENCES mcp_invocations(invocation_id) ON DELETE SET NULL,
    learner_id              UUID        REFERENCES learner_profiles(user_id) ON DELETE SET NULL,

    -- Raw vs optimised token counts (architecture.md §6)
    raw_schema_tokens       INT,
    pruned_schema_tokens    INT,
    raw_response_bytes      INT,
    projected_response_bytes INT,

    -- KV cache prefix alignment (left.md §2.3)
    kv_cache_hit            BOOLEAN     NOT NULL DEFAULT FALSE,
    kv_boundary_tokens      INT,                               -- token count of pinned prefix block

    -- Semantic compaction (left.md §2.4)
    history_turns_compacted INT,
    compacted_vector_dims   INT,

    recorded_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_token_opt_log_invocation ON token_optimization_log(invocation_id);


-- =============================================================================
-- SECTION 15 — NOTIFICATION ENGINE
-- Source: Mnemo/docs/NOTIFICATIONS.md; Mnemo/apple/Sources/NeuralLoopCore/Nudges.swift
-- =============================================================================

CREATE TYPE notification_type AS ENUM (
    'chapter_ready',   -- "Chapter N is ready to study"
    'nudge',           -- Pip daily nudge (once per day, respects quiet hours)
    'review_due',      -- FSRS cards due for review
    'loop_closed',     -- Congratulatory loop closed notification
    'sync_complete'    -- Background sync finished
);

CREATE TABLE notifications (
    notification_id         UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id              UUID                NOT NULL REFERENCES learner_profiles(user_id) ON DELETE CASCADE,
    chapter_id              UUID                REFERENCES chapters(chapter_id) ON DELETE SET NULL,

    type                    notification_type   NOT NULL,
    title                   TEXT                NOT NULL,
    body                    TEXT,
    delivered               BOOLEAN             NOT NULL DEFAULT FALSE,
    delivered_at            TIMESTAMPTZ,
    dismissed_at            TIMESTAMPTZ,

    created_at              TIMESTAMPTZ         NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_learner    ON notifications(learner_id, created_at DESC);
CREATE INDEX idx_notifications_undelivered ON notifications(learner_id) WHERE NOT delivered;


-- =============================================================================
-- SECTION 16 — SCHEMA VERSION METADATA
-- =============================================================================

CREATE TABLE schema_migrations (
    version                 TEXT        PRIMARY KEY,
    applied_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    description             TEXT
);

INSERT INTO schema_migrations (version, description)
VALUES ('001', 'Initial schema: learner identity, books, chapters, 5-stage loop, '
               'knowledge graph, FSRS, MCP gateway, episodic/semantic/procedural memory, '
               'verification sandbox, co-pilot interactions, token optimization audit, '
               'notifications.');
