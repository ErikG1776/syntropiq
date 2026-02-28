"""
Mutation Engine - Adaptive Threshold Adjustment

Implements Patent Claim 5: Trust mutation through dynamic threshold adjustment
based on system performance metrics.

Automatically tunes governance parameters:
- Trust threshold (minimum for agent assignment)
- Suppression threshold (triggers redemption cycles)
- Drift detection delta (sensitivity to performance changes)
"""

import os
from typing import Callable, Dict, List, Optional, TYPE_CHECKING
from syntropiq.core.invariants import Invariants, emit_violations
from syntropiq.core.models import ExecutionResult

if TYPE_CHECKING:
    from syntropiq.persistence.state_manager import PersistentStateManager


class MutationEngine:
    """
    Adaptive governance parameter tuning.
    
    Patent Claim 5: Adjusts trust thresholds based on system performance
    to optimize for safety (high thresholds) vs. throughput (low thresholds).
    """
    
    def __init__(
        self,
        initial_trust_threshold: float = 0.7,
        initial_suppression_threshold: float = 0.75,
        initial_drift_delta: float = 0.1,
        mutation_rate: float = 0.05,  # How much to adjust per cycle
        target_success_rate: float = 0.85,  # Target system performance
        state_manager: Optional["PersistentStateManager"] = None,
        history_window: int = 100,
        invariant_reporter: Optional[Callable[[List, Dict], None]] = None,
        warmup_cycles: int = int(os.getenv("MUTATION_WARMUP_CYCLES", "5")),
        max_step: float = float(os.getenv("MUTATION_MAX_STEP", "0.02")),
        suppression_dampen: bool = os.getenv("MUTATION_DAMPEN_ON_SUPPRESSION", "true").lower() == "true",
    ):
        """
        Initialize mutation engine.
        
        Args:
            initial_trust_threshold: Starting trust threshold
            initial_suppression_threshold: Starting suppression threshold
            initial_drift_delta: Starting drift detection sensitivity
            mutation_rate: How aggressively to adjust (0.01-0.1 recommended)
            target_success_rate: Desired system success rate (0.8-0.95 recommended)
            state_manager: Optional persistent state manager for DB-backed mutation state
            history_window: Number of recent mutation events to load for trend continuity
        """
        self.trust_threshold = initial_trust_threshold
        self.suppression_threshold = initial_suppression_threshold
        self.drift_delta = initial_drift_delta
        self.mutation_rate = mutation_rate
        self.target_success_rate = target_success_rate
        self.state_manager = state_manager
        self.history_window = history_window
        self.invariant_reporter = invariant_reporter
        self.warmup_cycles = warmup_cycles
        self.max_step = max_step
        self.suppression_dampen = suppression_dampen
        self.cycles_seen = 0
        self.suppression_seen = False
        
        # Performance history
        self.success_rates: List[float] = []
        self.mutation_history: List[Dict] = []

        self._load_persisted_state()

    def _load_persisted_state(self) -> None:
        """Load last mutation thresholds and history from persistent storage."""
        if not self.state_manager:
            return

        latest = self.state_manager.get_latest_mutation_thresholds()
        if latest:
            self.trust_threshold = latest["trust_threshold"]
            self.suppression_threshold = latest["suppression_threshold"]
            self.drift_delta = latest["drift_delta"]

        history = self.state_manager.get_mutation_history(limit=self.history_window)
        self.mutation_history = history
        self.success_rates = [event["success_rate"] for event in history]
    
    def evaluate_and_mutate(
        self,
        execution_results: List[ExecutionResult],
        cycle_id: str,
        suppression_active: bool = False,
    ) -> Dict[str, float]:
        """
        Evaluate system performance and adjust thresholds.
        
        Algorithm:
        - If success_rate < target: INCREASE thresholds (more conservative)
        - If success_rate > target: DECREASE thresholds (more aggressive)
        
        This creates a feedback loop that balances safety vs. throughput.
        
        Args:
            execution_results: Results from latest governance cycle
            cycle_id: Identifier for this cycle
            
        Returns:
            Dictionary of new threshold values
        """
        self.cycles_seen += 1
        if suppression_active:
            self.suppression_seen = True
        if not execution_results:
            return self._get_current_thresholds()
        
        # Calculate current success rate
        successes = sum(1 for r in execution_results if r.success)
        success_rate = successes / len(execution_results)
        self.success_rates.append(success_rate)
        
        print(f"\n🧬 Mutation Engine: Evaluating performance...")
        print(f"   Success rate: {success_rate:.1%} (target: {self.target_success_rate:.1%})")
        
        # Calculate performance delta
        delta = success_rate - self.target_success_rate
        
        # Mutate thresholds based on performance
        old_trust = self.trust_threshold
        old_suppression = self.suppression_threshold
        old_drift = self.drift_delta
        
        trust_delta = 0.0
        suppression_delta = 0.0
        drift_delta = 0.0

        if delta < -0.05:  # Significantly below target
            # System performing poorly - INCREASE thresholds (more conservative)
            trust_delta = self.mutation_rate * 0.2
            suppression_delta = 0.0
            drift_delta = 0.01
            action = "TIGHTENING (poor performance)"
        elif delta > 0.05:  # Significantly above target
            # System performing well - DECREASE thresholds (more aggressive)
            trust_delta = -self.mutation_rate
            suppression_delta = -self.mutation_rate
            drift_delta = -0.02
            action = "LOOSENING (excellent performance)"
        else:
            # Performance near target - hold thresholds stable.
            action = "STABLE (near target)"

        # Rule A: during warmup, block all loosening moves.
        warmup_blocked = False
        if self.cycles_seen <= self.warmup_cycles and any(x < 0 for x in (trust_delta, suppression_delta, drift_delta)):
            trust_delta = max(0.0, trust_delta)
            suppression_delta = max(0.0, suppression_delta)
            drift_delta = max(0.0, drift_delta)
            warmup_blocked = True

        # Rule C: if suppression is active, do not loosen.
        suppression_blocked = False
        if suppression_active and self.suppression_dampen:
            if trust_delta < 0:
                trust_delta = 0.0
                suppression_blocked = True
            if suppression_delta < 0:
                suppression_delta = 0.0
                suppression_blocked = True
            if drift_delta < 0:
                drift_delta = 0.0
                suppression_blocked = True
            # Keep routing recoverable under active suppression:
            # do not continue tightening trust/suppression gates while suppressed.
            if trust_delta > 0:
                trust_delta = 0.0
                suppression_blocked = True
            if suppression_delta > 0:
                suppression_delta = 0.0
                suppression_blocked = True

        # Rule B: cap all per-cycle movements.
        trust_delta = max(-self.max_step, min(self.max_step, trust_delta))
        suppression_delta = max(-self.max_step, min(self.max_step, suppression_delta))
        drift_delta = max(-self.max_step, min(self.max_step, drift_delta))

        new_trust = self.trust_threshold + trust_delta
        new_suppression = self.suppression_threshold + suppression_delta
        new_drift = self.drift_delta + drift_delta

        # Rule D: enforce bounds and safety band.
        new_trust = max(0.50, min(0.95, new_trust))
        if self.suppression_dampen and self.suppression_seen:
            # Keep trust gate recoverable after suppression has started.
            new_trust = min(new_trust, 0.71)
        # Ensure suppression ceiling can still satisfy suppression >= trust + 0.05.
        new_trust = min(new_trust, 0.90)
        new_suppression = max(max(0.60, new_trust + 0.05), min(0.95, new_suppression))
        new_drift = max(0.05, min(0.20, new_drift))

        self.trust_threshold = new_trust
        self.suppression_threshold = new_suppression
        self.drift_delta = new_drift

        if warmup_blocked and abs(self.trust_threshold - old_trust) < 1e-12:
            action = "STABLE (warmup)"
        elif suppression_blocked and abs(self.trust_threshold - old_trust) < 1e-12:
            action = "STABLE (suppression dampened)"
        
        # Record mutation
        mutation_record = {
            "cycle_id": cycle_id,
            "success_rate": success_rate,
            "action": action,
            "trust_threshold": {"old": old_trust, "new": self.trust_threshold},
            "suppression_threshold": {"old": old_suppression, "new": self.suppression_threshold},
            "drift_delta": {"old": old_drift, "new": self.drift_delta}
        }
        self.mutation_history.append(mutation_record)
        if self.state_manager:
            self.state_manager.record_mutation_event(mutation_record)
        
        # Print mutation results
        if old_trust != self.trust_threshold:
            print(f"   🔧 {action}")
            print(f"   • Trust threshold: {old_trust:.2f} → {self.trust_threshold:.2f}")
            if old_suppression != self.suppression_threshold:
                print(f"   • Suppression threshold: {old_suppression:.2f} → {self.suppression_threshold:.2f}")
            if old_drift != self.drift_delta:
                print(f"   • Drift delta: {old_drift:.2f} → {self.drift_delta:.2f}")
        else:
            print(f"   ✓ Thresholds stable (performance on target)")

        violations = []
        violations.extend(Invariants.check_tau_range(self.trust_threshold))
        violations.extend(Invariants.check_delta_bound(self.trust_threshold - old_trust))

        if violations:
            base_metadata = {
                "run_id": cycle_id.split(":")[0] if ":" in cycle_id else cycle_id,
                "cycle_id": cycle_id,
                "timestamp": mutation_record.get("timestamp", ""),
                "component": "mutation_engine",
            }
            if self.invariant_reporter is not None:
                try:
                    self.invariant_reporter(violations, base_metadata)
                except Exception:
                    pass
            else:
                # TODO(phase-2): centralize reporter wiring; this fallback remains non-blocking.
                emit_violations(None, violations, base_metadata)

        return self._get_current_thresholds()
    
    def _get_current_thresholds(self) -> Dict[str, float]:
        """Get current threshold values."""
        return {
            "trust_threshold": self.trust_threshold,
            "suppression_threshold": self.suppression_threshold,
            "drift_delta": self.drift_delta
        }
    
    def get_mutation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent mutation events."""
        if self.state_manager:
            return self.state_manager.get_mutation_history(limit=limit)
        return self.mutation_history[-limit:]
    
    def get_performance_trend(self) -> Dict:
        """Get performance trend statistics."""
        if not self.success_rates:
            return {"avg_success_rate": 0.0, "trend": "unknown", "cycles_tracked": 0}
        
        recent = self.success_rates[-10:]  # Last 10 cycles
        avg = sum(recent) / len(recent)
        
        # Calculate trend
        if len(recent) >= 2:
            first_half = sum(recent[:len(recent)//2]) / (len(recent)//2)
            second_half = sum(recent[len(recent)//2:]) / (len(recent) - len(recent)//2)
            trend = "improving" if second_half > first_half else "declining"
        else:
            trend = "stable"
        
        return {
            "avg_success_rate": round(avg, 3),
            "trend": trend,
            "cycles_tracked": len(self.success_rates)
        }
