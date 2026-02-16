"""
Mutation Engine - Adaptive Threshold Adjustment

Implements Patent Claim 5: Trust mutation through dynamic threshold adjustment
based on system performance metrics.

Automatically tunes governance parameters:
- Trust threshold (minimum for agent assignment)
- Suppression threshold (triggers redemption cycles)
- Drift detection delta (sensitivity to performance changes)
"""

from typing import Dict, List, Optional, TYPE_CHECKING
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
        history_window: int = 100
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
        cycle_id: str
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
        
        if delta < -0.05:  # Significantly below target
            # System performing poorly - INCREASE thresholds (more conservative)
            self.trust_threshold = min(0.95, self.trust_threshold + self.mutation_rate)
            self.suppression_threshold = min(0.95, self.suppression_threshold + self.mutation_rate)
            self.drift_delta = min(0.2, self.drift_delta + 0.02)
            action = "TIGHTENING (poor performance)"
            
        elif delta > 0.05:  # Significantly above target
            # System performing well - DECREASE thresholds (more aggressive)
            self.trust_threshold = max(0.55, self.trust_threshold - self.mutation_rate)
            self.suppression_threshold = max(0.78, self.suppression_threshold - self.mutation_rate)
            self.drift_delta = max(0.05, self.drift_delta - 0.02)
            action = "LOOSENING (excellent performance)"

        else:
            # Performance near target - minor adjustments
            if delta < 0:
                self.trust_threshold = min(0.95, self.trust_threshold + self.mutation_rate * 0.5)
                action = "MINOR TIGHTENING"
            else:
                self.trust_threshold = max(0.55, self.trust_threshold - self.mutation_rate * 0.5)
                action = "MINOR LOOSENING"

        # Enforce minimum safety band: suppression >= trust + 0.05
        required_suppression = self.trust_threshold + 0.05
        if self.suppression_threshold < required_suppression:
            if required_suppression <= 0.95:
                self.suppression_threshold = required_suppression
            else:
                self.suppression_threshold = 0.95
                self.trust_threshold = min(self.trust_threshold, self.suppression_threshold - 0.05)
        
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
