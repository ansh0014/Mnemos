"""Stage 4 Challenge Orchestrator Handler managing the 5-Beat Discovery State Machine."""

from __future__ import annotations

from typing import Any

from mnemos_services.memory_engine.episodic.store import CognitiveMemoryStore
from mnemos_services.memory_engine.semantic.graph_memory import SemanticGraphMemory

from ..models.schemas import LabBeatNumber
from ..scenarios.labs import LAB_DEFINITIONS, execute_lab_beat


class ChallengeHandler:
    """Coordinates 5-Beat Discovery transitions, episodic failure logs, and mastery unlocks."""

    def __init__(
        self,
        memory_store: CognitiveMemoryStore | None = None,
        semantic_memory: SemanticGraphMemory | None = None,
    ) -> None:
        self.memory_store = memory_store or CognitiveMemoryStore(":memory:")
        self.semantic_memory = semantic_memory or SemanticGraphMemory()
        self._progress: dict[tuple[str, str], LabBeatNumber] = {}

    def get_beat_spec(self, lab_id: str, beat: LabBeatNumber = 1) -> dict[str, Any]:
        lab = LAB_DEFINITIONS.get(lab_id)
        if lab is None:
            raise KeyError(f"Unknown lab_id: {lab_id}")
        return lab.get_public_beat_payload(beat)

    def configure_simulation_scenario(self, lab_id: str, user_id: str = "default") -> dict[str, Any]:
        """Start or resume a lab at its current unlocked Beat (masking Beat 5 jargon until unlocked)."""
        current_beat = self._progress.get((user_id, lab_id), 1)
        payload = self.get_beat_spec(lab_id, current_beat)
        payload["unlocked_beat"] = current_beat
        return payload

    def run_beat_verification(
        self,
        lab_id: str,
        beat: LabBeatNumber,
        user_code: str,
        mode: str = "unit_tests",
        user_id: str = "default",
    ) -> dict[str, Any]:
        """Run user code against unit tests or stress harness and advance Beat state on milestones."""
        lab = LAB_DEFINITIONS[lab_id]
        exec_res = execute_lab_beat(lab_id, beat, user_code, mode=mode)
        response = exec_res.to_dict()
        next_beat: LabBeatNumber = self._progress.get((user_id, lab_id), beat)

        if beat == 1 and mode == "unit_tests" and exec_res.all_tests_passed:
            next_beat = max(next_beat, 2)  # type: ignore[assignment]
        elif beat == 2 and mode == "stress_simulation" and exec_res.simulation_trace:
            if exec_res.simulation_trace.failed_as_expected_in_beat2:
                next_beat = max(next_beat, 3)  # type: ignore[assignment]
                alert_title = (exec_res.simulation_trace.headline_alert or {}).get("title", "stress_failure")
                self.memory_store.log_episodic_event(
                    stage="verification_harness",
                    failure_mode_observed=f"{lab_id}: {alert_title}",
                    user_id=user_id,
                    concept_id=lab.concept_node_id,
                    simulation_id=exec_res.simulation_trace.scenario_name,
                )
        elif beat == 4 and exec_res.simulation_trace and exec_res.simulation_trace.passed_stress_in_beat4:
            # Verify evolved code also passes all Beat 4 behavioral unit tests before unlocking Beat 5.
            ut_check = execute_lab_beat(lab_id, 4, user_code, mode="unit_tests")
            response["beat4_unit_tests_passed"] = ut_check.all_tests_passed
            if ut_check.all_tests_passed:
                next_beat = 5
                node = self.semantic_memory.get_node(lab.concept_node_id)
                self.memory_store.update_concept_mastery(
                    concept_id=lab.concept_node_id,
                    domain=node["domain"] if node else "systems",
                    canonical_name=node["title"] if node else lab.title,
                    score=1.0,
                    passed=True,
                )

        self._progress[(user_id, lab_id)] = next_beat
        response["unlocked_beat"] = next_beat
        return response

    def submit_diagnosis(self, lab_id: str, option_id: str, user_id: str = "default") -> dict[str, Any]:
        """Evaluate Beat 3 intuitive root-cause diagnosis and unlock Beat 4 on success."""
        lab = LAB_DEFINITIONS.get(lab_id)
        if lab is None or lab.beats[3].diagnosis is None:
            raise KeyError(f"Diagnosis not configured for lab: {lab_id}")

        for opt in lab.beats[3].diagnosis.options:
            if opt.id == option_id:
                if opt.is_correct:
                    current = self._progress.get((user_id, lab_id), 3)
                    self._progress[(user_id, lab_id)] = max(current, 4)  # type: ignore[assignment]
                    return {
                        "correct": True,
                        "feedback": opt.feedback,
                        "unlocked_beat": self._progress[(user_id, lab_id)],
                    }
                self.memory_store.record_misconception(
                    concept_id=lab.concept_node_id,
                    fallacy_category="beat3_diagnosis_miss",
                    diagnostic_summary=opt.label,
                    triggering_pattern=option_id,
                    user_id=user_id,
                )
                return {
                    "correct": False,
                    "feedback": opt.feedback,
                    "unlocked_beat": self._progress.get((user_id, lab_id), 3),
                }
        raise ValueError(f"Unknown diagnosis option_id: {option_id}")

    def extract_concept_nodes(self, lab_id: str) -> dict[str, Any]:
        """Return Grand Scheme node and prerequisite context for a lab."""
        lab = LAB_DEFINITIONS[lab_id]
        node = self.semantic_memory.get_node(lab.concept_node_id)
        prereqs = self.semantic_memory.get_prerequisites(lab.concept_node_id)
        downs = self.semantic_memory.get_downstream_dependents(lab.concept_node_id)
        return {"lab_id": lab_id, "node": node, "prerequisites": prereqs, "downstream": downs}
