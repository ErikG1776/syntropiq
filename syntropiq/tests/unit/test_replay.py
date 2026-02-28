from syntropiq.core.replay import compare_runs, compute_r, load_run_artifacts, replay_run


class _FakeStateManager:
    def load_cycles_by_run_id(self, run_id: str, limit: int = 2000):
        assert run_id == "RUN_A"
        return [
            {"run_id": "RUN_A", "cycle_id": "RUN_A:1", "timestamp": "2026-02-28T00:00:00Z"},
            {"run_id": "RUN_A", "cycle_id": "RUN_A:2", "timestamp": "2026-02-28T00:00:01Z"},
            {"run_id": "RUN_A", "cycle_id": "RUN_A:3", "timestamp": "2026-02-28T00:00:02Z"},
        ]

    def load_events_by_run_id(self, run_id: str, limit: int = 5000):
        assert run_id == "RUN_A"
        return [
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:1",
                "type": "mediation_decision",
                "metadata": {"selected_agents": ["alpha"]},
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:1",
                "type": "trust_update",
                "agent_id": "alpha",
                "trust_after": 0.82,
                "metadata": {},
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:1",
                "type": "mutation",
                "metadata": {
                    "trust_threshold": 0.70,
                    "suppression_threshold": 0.75,
                    "drift_delta": 0.10,
                },
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:2",
                "type": "mediation_decision",
                "metadata": {"selected_agents": ["alpha"]},
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:2",
                "type": "trust_update",
                "agent_id": "alpha",
                "trust_after": 0.84,
                "metadata": {},
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:2",
                "type": "mutation",
                "metadata": {
                    "trust_threshold": 0.69,
                    "suppression_threshold": 0.74,
                    "drift_delta": 0.09,
                },
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:2",
                "type": "suppression",
                "agent_id": "beta",
                "metadata": {"status_after": "suppressed"},
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:3",
                "type": "mediation_decision",
                "metadata": {"selected_agents": ["gamma"]},
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:3",
                "type": "trust_update",
                "agent_id": "gamma",
                "trust_after": 0.79,
                "metadata": {},
            },
            {
                "run_id": "RUN_A",
                "cycle_id": "RUN_A:3",
                "type": "mutation",
                "metadata": {
                    "trust_threshold": 0.68,
                    "suppression_threshold": 0.73,
                    "drift_delta": 0.08,
                },
            },
        ]


def _base_original():
    return {
        "run_id": "RUN_X",
        "cycles": [
            {
                "cycle_id": "RUN_X:1",
                "selected_agents": ["alpha"],
                "suppressed_agents": [],
                "trust_after": {"alpha": 0.8, "beta": 0.7},
                "mutation": {"trust_threshold": 0.7, "suppression_threshold": 0.75, "drift_delta": 0.1},
            },
            {
                "cycle_id": "RUN_X:2",
                "selected_agents": ["beta"],
                "suppressed_agents": ["alpha"],
                "trust_after": {"alpha": 0.75, "beta": 0.72},
                "mutation": {"trust_threshold": 0.69, "suppression_threshold": 0.74, "drift_delta": 0.09},
            },
            {
                "cycle_id": "RUN_X:3",
                "selected_agents": ["gamma"],
                "suppressed_agents": ["alpha"],
                "trust_after": {"alpha": 0.74, "beta": 0.73, "gamma": 0.81},
                "mutation": {"trust_threshold": 0.68, "suppression_threshold": 0.73, "drift_delta": 0.08},
            },
        ],
    }


def test_replay_identical_run_scores_one():
    original = _base_original()
    replayed = {"run_id": "RUN_X", "mode": "light", "cycles": [dict(c) for c in original["cycles"]]}

    comparison = compare_runs(original, replayed)
    assert comparison.selection_match == 1.0
    assert comparison.suppression_match == 1.0
    assert comparison.trust_corr == 1.0
    assert comparison.threshold_corr == 1.0
    assert compute_r(comparison) == 1.0


def test_replay_trust_change_reduces_r():
    original = _base_original()
    replayed_cycles = [dict(c) for c in original["cycles"]]
    replayed_cycles[1] = dict(replayed_cycles[1])
    replayed_cycles[1]["trust_after"] = dict(replayed_cycles[1]["trust_after"])
    replayed_cycles[1]["trust_after"]["beta"] = 0.40

    comparison = compare_runs(original, {"run_id": "RUN_X", "mode": "light", "cycles": replayed_cycles})
    assert comparison.trust_corr < 1.0
    assert compute_r(comparison) < 1.0


def test_replay_selection_mismatch_reduces_selection_component():
    original = _base_original()
    replayed_cycles = [dict(c) for c in original["cycles"]]
    replayed_cycles[0] = dict(replayed_cycles[0])
    replayed_cycles[0]["selected_agents"] = ["beta"]

    comparison = compare_runs(original, {"run_id": "RUN_X", "mode": "light", "cycles": replayed_cycles})
    assert comparison.selection_match == 2 / 3
    assert compute_r(comparison) < 1.0


def test_full_mode_falls_back_to_light_when_artifacts_insufficient():
    manager = _FakeStateManager()
    artifacts = load_run_artifacts(manager, "RUN_A")
    replayed = replay_run(artifacts, seed=123, mode="full")

    assert replayed["mode"] == "light"
    assert "full replay unavailable" in (replayed.get("explanation") or "")
    assert len(replayed.get("cycles") or []) == 3
