"""SQLite-backed Episodic Memory, Misconceptions, Mastery, and FSRS-4.5 Scheduler.

Implements the cognitive ER schema from ``architecture.md`` Section 8 and ``plan.md``
Section 6 with exponential time-decay scoring and deterministic FSRS-4.5 math.
"""

from __future__ import annotations

import math
import sqlite3
import time
import uuid
from typing import Any


class CognitiveMemoryStore:
    """Persistent (or in-memory) SQLite store for learner memory and spaced reviews."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS learner_profile (
                user_id TEXT PRIMARY KEY,
                preferred_learning_style TEXT DEFAULT 'first_principles',
                retention_target REAL DEFAULT 0.90,
                last_synced REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS concept_mastery (
                concept_id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                canonical_name TEXT NOT NULL,
                mastery_score REAL DEFAULT 0.0,
                total_recall_attempts INTEGER DEFAULT 0,
                failed_recall_attempts INTEGER DEFAULT 0,
                last_tested_at REAL
            );

            CREATE TABLE IF NOT EXISTS episodic_log (
                log_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                concept_id TEXT,
                simulation_id TEXT,
                failure_mode_observed TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES learner_profile(user_id)
            );

            CREATE TABLE IF NOT EXISTS misconceptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                concept_id TEXT NOT NULL,
                fallacy_category TEXT NOT NULL,
                diagnostic_summary TEXT NOT NULL,
                triggering_pattern TEXT DEFAULT '',
                resolved INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                resolved_at REAL,
                FOREIGN KEY(user_id) REFERENCES learner_profile(user_id)
            );

            CREATE TABLE IF NOT EXISTS fsrs_cards (
                card_id TEXT PRIMARY KEY,
                concept_id TEXT NOT NULL,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                stability REAL DEFAULT 1.0,
                difficulty REAL DEFAULT 5.0,
                reps INTEGER DEFAULT 0,
                lapses INTEGER DEFAULT 0,
                due_timestamp REAL NOT NULL,
                last_reviewed_at REAL,
                current_state INTEGER DEFAULT 0
            );
            """
        )
        self._conn.commit()

    def ensure_learner(self, user_id: str = "default", retention_target: float = 0.90) -> dict[str, Any]:
        now = time.time()
        self._conn.execute(
            """
            INSERT INTO learner_profile (user_id, retention_target, last_synced)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_synced = excluded.last_synced
            """,
            (user_id, retention_target, now),
        )
        self._conn.commit()
        row = self._conn.execute("SELECT * FROM learner_profile WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row)

    def log_episodic_event(
        self,
        stage: str,
        failure_mode_observed: str,
        user_id: str = "default",
        concept_id: str | None = None,
        simulation_id: str | None = None,
        created_at: float | None = None,
    ) -> str:
        self.ensure_learner(user_id)
        log_id = f"ep-{uuid.uuid4().hex[:12]}"
        ts = time.time() if created_at is None else created_at
        self._conn.execute(
            """
            INSERT INTO episodic_log
            (log_id, user_id, stage, concept_id, simulation_id, failure_mode_observed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (log_id, user_id, stage, concept_id, simulation_id, failure_mode_observed, ts),
        )
        self._conn.commit()
        return log_id

    def get_recent_failures(
        self,
        user_id: str = "default",
        concept_id: str | None = None,
        decay_lambda_per_day: float = 0.25,
        now: float | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve episodic failures weighted by exponential time decay exp(-lambda * days)."""
        current = time.time() if now is None else now
        if concept_id:
            rows = self._conn.execute(
                "SELECT * FROM episodic_log WHERE user_id = ? AND concept_id = ? ORDER BY created_at DESC",
                (user_id, concept_id),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM episodic_log WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

        weighted: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            age_days = max(0.0, (current - float(item["created_at"])) / 86400.0)
            item["temporal_decay_weight"] = round(math.exp(-decay_lambda_per_day * age_days), 6)
            weighted.append(item)
        weighted.sort(key=lambda r: r["temporal_decay_weight"], reverse=True)
        return weighted[:limit]

    def record_misconception(
        self,
        concept_id: str,
        fallacy_category: str,
        diagnostic_summary: str,
        triggering_pattern: str = "",
        user_id: str = "default",
    ) -> str:
        self.ensure_learner(user_id)
        misc_id = f"mc-{uuid.uuid4().hex[:12]}"
        self._conn.execute(
            """
            INSERT INTO misconceptions
            (id, user_id, concept_id, fallacy_category, diagnostic_summary, triggering_pattern, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (misc_id, user_id, concept_id, fallacy_category, diagnostic_summary, triggering_pattern, time.time()),
        )
        self._conn.commit()
        return misc_id

    def resolve_misconceptions(self, concept_id: str, user_id: str = "default") -> int:
        cur = self._conn.execute(
            """
            UPDATE misconceptions
            SET resolved = 1, resolved_at = ?
            WHERE user_id = ? AND concept_id = ? AND resolved = 0
            """,
            (time.time(), user_id, concept_id),
        )
        self._conn.commit()
        return cur.rowcount

    def get_misconceptions(
        self,
        concept_id: str | None = None,
        unresolved_only: bool = True,
        user_id: str = "default",
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM misconceptions WHERE user_id = ?"
        params: list[Any] = [user_id]
        if concept_id:
            query += " AND concept_id = ?"
            params.append(concept_id)
        if unresolved_only:
            query += " AND resolved = 0"
        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def update_concept_mastery(
        self,
        concept_id: str,
        domain: str,
        canonical_name: str,
        score: float,
        passed: bool,
    ) -> dict[str, Any]:
        now = time.time()
        existing = self._conn.execute(
            "SELECT * FROM concept_mastery WHERE concept_id = ?", (concept_id,)
        ).fetchone()
        if existing is None:
            self._conn.execute(
                """
                INSERT INTO concept_mastery
                (concept_id, domain, canonical_name, mastery_score, total_recall_attempts,
                 failed_recall_attempts, last_tested_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (concept_id, domain, canonical_name, score, 0 if passed else 1, now),
            )
        else:
            blended = round(0.4 * float(existing["mastery_score"]) + 0.6 * score, 4)
            self._conn.execute(
                """
                UPDATE concept_mastery
                SET mastery_score = ?,
                    total_recall_attempts = total_recall_attempts + 1,
                    failed_recall_attempts = failed_recall_attempts + ?,
                    last_tested_at = ?
                WHERE concept_id = ?
                """,
                (blended, 0 if passed else 1, now, concept_id),
            )
        self._conn.commit()
        row = self._conn.execute("SELECT * FROM concept_mastery WHERE concept_id = ?", (concept_id,)).fetchone()
        return dict(row)

    def create_atomic_card(
        self,
        concept_id: str,
        front: str,
        back: str,
        due_timestamp: float | None = None,
    ) -> dict[str, Any]:
        card_id = f"card-{uuid.uuid4().hex[:10]}"
        due = time.time() if due_timestamp is None else due_timestamp
        self._conn.execute(
            """
            INSERT INTO fsrs_cards (card_id, concept_id, front, back, due_timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (card_id, concept_id, front, back, due),
        )
        self._conn.commit()
        return dict(self._conn.execute("SELECT * FROM fsrs_cards WHERE card_id = ?", (card_id,)).fetchone())

    def get_due_fsrs_cards(self, now: float | None = None, limit: int = 20) -> list[dict[str, Any]]:
        current = time.time() if now is None else now
        rows = self._conn.execute(
            "SELECT * FROM fsrs_cards WHERE due_timestamp <= ? ORDER BY due_timestamp ASC LIMIT ?",
            (current, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def schedule_fsrs_review(
        self,
        card_id: str,
        rating: int,
        now: float | None = None,
        retention_target: float = 0.90,
    ) -> dict[str, Any]:
        """Deterministic FSRS-4.5 review update for ratings 1 (Again), 2 (Hard), 3 (Good), 4 (Easy)."""
        if rating not in (1, 2, 3, 4):
            raise ValueError("FSRS rating must be 1..4")
        row = self._conn.execute("SELECT * FROM fsrs_cards WHERE card_id = ?", (card_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown card_id: {card_id}")

        current = time.time() if now is None else now
        stability = float(row["stability"])
        difficulty = float(row["difficulty"])
        reps = int(row["reps"])
        lapses = int(row["lapses"])
        last_rev = row["last_reviewed_at"]

        elapsed_days = max(0.0, (current - float(last_rev)) / 86400.0) if last_rev else 0.0
        # Retrievability curve from FSRS-4.5: R = (1 + t / (9 * S))^-1
        retrievability = math.pow(1.0 + elapsed_days / (9.0 * max(0.1, stability)), -1.0)

        # Difficulty update clamped to [1.0, 10.0]
        difficulty = max(1.0, min(10.0, difficulty - 0.65 * (rating - 3)))

        if rating == 1:
            lapses += 1
            reps = 0
            stability = max(0.4, round(stability * 0.45, 4))
            interval_days = 0.25  # relearn in 6 hours
            state = 3  # Relearning
        else:
            reps += 1
            rating_gain = {2: 1.25, 3: 2.1, 4: 3.0}[rating]
            recall_boost = 1.0 + (1.0 - retrievability) * 0.8
            stability = round(max(0.5, stability * rating_gain * recall_boost * (1.0 - 0.03 * (difficulty - 5.0))), 4)
            # Interval in days targeting requested retention: I = 9 * S * (1/R_target - 1)
            interval_days = max(1.0, round(9.0 * stability * (1.0 / retention_target - 1.0), 2))
            state = 2  # Review

        due_ts = current + interval_days * 86400.0
        self._conn.execute(
            """
            UPDATE fsrs_cards
            SET stability = ?, difficulty = ?, reps = ?, lapses = ?,
                due_timestamp = ?, last_reviewed_at = ?, current_state = ?
            WHERE card_id = ?
            """,
            (stability, round(difficulty, 4), reps, lapses, due_ts, current, state, card_id),
        )
        self._conn.commit()
        updated = dict(self._conn.execute("SELECT * FROM fsrs_cards WHERE card_id = ?", (card_id,)).fetchone())
        updated["retrievability"] = round(retrievability, 4)
        updated["next_interval_days"] = interval_days
        return updated
