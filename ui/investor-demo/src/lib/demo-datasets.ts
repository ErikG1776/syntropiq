import type { DemoDataset, DomainId } from "./demo-data";

export const DEMO_DATASETS: Record<DomainId, DemoDataset> = {
  "lending": {
    "config": {
      "num_cycles": 35,
      "batch_size": 15,
      "routing_mode": "competitive",
      "drift_agent": "growth",
      "drift_rate": 0.03,
      "drift_start_cycle": 3,
      "agent_profiles": {
        "conservative": 0.25,
        "balanced": 0.35,
        "growth": 0.4
      }
    },
    "final_state": {
      "trust_scores": {
        "conservative": 1.0,
        "balanced": 1.0,
        "growth": 0.92
      },
      "trust_threshold": 0.7,
      "suppression_threshold": 0.8,
      "drift_tolerance_final": 0.95
    },
    "timeline": [
      {
        "cycle": 0,
        "phase": "RAMP-UP (mixed loans)",
        "status": "circuit_breaker",
        "trust_scores": {
          "conservative": 0.8,
          "balanced": 0.81,
          "growth": 0.83
        }
      },
      {
        "cycle": 1,
        "phase": "RAMP-UP (mixed loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.87,
          "balanced": 0.87,
          "growth": 0.87
        },
        "trust_threshold": 0.76,
        "suppression_threshold": 0.82,
        "drift_tolerance": 0.4,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 15,
        "failures": 0,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 2,
        "phase": "RAMP-UP (mixed loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.89,
          "balanced": 0.89,
          "growth": 0.89
        },
        "trust_threshold": 0.75,
        "suppression_threshold": 0.82,
        "drift_tolerance": 0.4,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 7652.0
      },
      {
        "cycle": 3,
        "phase": "RAMP-UP (mixed loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.91,
          "balanced": 0.91,
          "growth": 0.91
        },
        "trust_threshold": 0.74,
        "suppression_threshold": 0.82,
        "drift_tolerance": 0.43,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 3972.0
      },
      {
        "cycle": 4,
        "phase": "RAMP-UP (mixed loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.93,
          "balanced": 0.93,
          "growth": 0.93
        },
        "trust_threshold": 0.73,
        "suppression_threshold": 0.82,
        "drift_tolerance": 0.46,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 11990.0
      },
      {
        "cycle": 5,
        "phase": "RAMP-UP (mixed loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.95,
          "balanced": 0.95,
          "growth": 0.95
        },
        "trust_threshold": 0.71,
        "suppression_threshold": 0.8,
        "drift_tolerance": 0.49,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 15,
        "failures": 0,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 6,
        "phase": "RAMP-UP (mixed loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.97,
          "balanced": 0.97,
          "growth": 0.97
        },
        "trust_threshold": 0.72,
        "suppression_threshold": 0.8,
        "drift_tolerance": 0.52,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 2,
        "potential_loss": 33915.0
      },
      {
        "cycle": 7,
        "phase": "RAMP-UP (mixed loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.99,
          "balanced": 0.99,
          "growth": 0.99
        },
        "trust_threshold": 0.7,
        "suppression_threshold": 0.78,
        "drift_tolerance": 0.55,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 15,
        "failures": 0,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 8,
        "phase": "RAMP-UP (mixed loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 1.0
        },
        "trust_threshold": 0.68,
        "suppression_threshold": 0.76,
        "drift_tolerance": 0.58,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 15,
        "failures": 0,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 9,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 1.0
        },
        "trust_threshold": 0.66,
        "suppression_threshold": 0.74,
        "drift_tolerance": 0.61,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 15,
        "failures": 0,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 10,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 1.0
        },
        "trust_threshold": 0.65,
        "suppression_threshold": 0.74,
        "drift_tolerance": 0.64,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 11,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.95
        },
        "trust_threshold": 0.64,
        "suppression_threshold": 0.74,
        "drift_tolerance": 0.67,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 4547.0
      },
      {
        "cycle": 12,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.9
        },
        "trust_threshold": 0.65,
        "suppression_threshold": 0.74,
        "drift_tolerance": 0.7,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 13,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.85
        },
        "trust_threshold": 0.64,
        "suppression_threshold": 0.74,
        "drift_tolerance": 0.73,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 14,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.87
        },
        "trust_threshold": 0.62,
        "suppression_threshold": 0.72,
        "drift_tolerance": 0.76,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 15,
        "failures": 0,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 15,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.89
        },
        "trust_threshold": 0.63,
        "suppression_threshold": 0.72,
        "drift_tolerance": 0.79,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 16,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.84
        },
        "trust_threshold": 0.62,
        "suppression_threshold": 0.72,
        "drift_tolerance": 0.82,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 17,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.86
        },
        "trust_threshold": 0.61,
        "suppression_threshold": 0.72,
        "drift_tolerance": 0.85,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 18,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.81
        },
        "trust_threshold": 0.62,
        "suppression_threshold": 0.72,
        "drift_tolerance": 0.88,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 2,
        "potential_loss": 11351.0
      },
      {
        "cycle": 19,
        "phase": "STRESS (drift accelerating)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.83
        },
        "trust_threshold": 0.64,
        "suppression_threshold": 0.74,
        "drift_tolerance": 0.91,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 11,
        "failures": 4,
        "bad_approvals": 3,
        "potential_loss": 40163.0
      },
      {
        "cycle": 20,
        "phase": "RECOVERY (safe loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.85
        },
        "trust_threshold": 0.65,
        "suppression_threshold": 0.74,
        "drift_tolerance": 0.94,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 2,
        "potential_loss": 38418.0
      },
      {
        "cycle": 21,
        "phase": "RECOVERY (safe loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.87
        },
        "trust_threshold": 0.63,
        "suppression_threshold": 0.72,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 15,
        "failures": 0,
        "bad_approvals": 0,
        "potential_loss": 0
      },
      {
        "cycle": 22,
        "phase": "RECOVERY (safe loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.95,
          "growth": 0.89
        },
        "trust_threshold": 0.62,
        "suppression_threshold": 0.72,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 3920.0
      },
      {
        "cycle": 23,
        "phase": "RECOVERY (safe loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.97,
          "growth": 0.91
        },
        "trust_threshold": 0.64,
        "suppression_threshold": 0.74,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 12,
        "failures": 3,
        "bad_approvals": 3,
        "potential_loss": 56495.0
      },
      {
        "cycle": 24,
        "phase": "RECOVERY (safe loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.92,
          "growth": 0.86
        },
        "trust_threshold": 0.66,
        "suppression_threshold": 0.76,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 12,
        "failures": 3,
        "bad_approvals": 3,
        "potential_loss": 25960.0
      },
      {
        "cycle": 25,
        "phase": "RECOVERY (safe loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.94,
          "growth": 0.88
        },
        "trust_threshold": 0.67,
        "suppression_threshold": 0.76,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 2,
        "potential_loss": 36486.0
      },
      {
        "cycle": 26,
        "phase": "RECOVERY (safe loans)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.96,
          "growth": 0.9
        },
        "trust_threshold": 0.66,
        "suppression_threshold": 0.76,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 14725.0
      },
      {
        "cycle": 27,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.98,
          "growth": 0.92
        },
        "trust_threshold": 0.65,
        "suppression_threshold": 0.76,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 14631.0
      },
      {
        "cycle": 28,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.94
        },
        "trust_threshold": 0.67,
        "suppression_threshold": 0.78,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 12,
        "failures": 3,
        "bad_approvals": 1,
        "potential_loss": 19263.0
      },
      {
        "cycle": 29,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.96
        },
        "trust_threshold": 0.68,
        "suppression_threshold": 0.78,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 2,
        "potential_loss": 52492.0
      },
      {
        "cycle": 30,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.91
        },
        "trust_threshold": 0.69,
        "suppression_threshold": 0.78,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 1,
        "potential_loss": 6693.0
      },
      {
        "cycle": 31,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.95,
          "growth": 0.86
        },
        "trust_threshold": 0.71,
        "suppression_threshold": 0.8,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 9,
        "failures": 6,
        "bad_approvals": 4,
        "potential_loss": 67349.0
      },
      {
        "cycle": 32,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.97,
          "growth": 0.88
        },
        "trust_threshold": 0.7,
        "suppression_threshold": 0.8,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 17750.0
      },
      {
        "cycle": 33,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 0.99,
          "growth": 0.9
        },
        "trust_threshold": 0.71,
        "suppression_threshold": 0.8,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 13,
        "failures": 2,
        "bad_approvals": 1,
        "potential_loss": 23617.0
      },
      {
        "cycle": 34,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "balanced": 1.0,
          "growth": 0.92
        },
        "trust_threshold": 0.7,
        "suppression_threshold": 0.8,
        "drift_tolerance": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 14,
        "failures": 1,
        "bad_approvals": 1,
        "potential_loss": 26307.0
      }
    ]
  },
  "fraud": {
    "config": {
      "num_cycles": 30,
      "batch_size": 8,
      "routing_mode": "competitive",
      "data_source": "Synthetic (IEEE-CIS distributions)",
      "drift_agent": "ensemble",
      "drift_rate": 0.04,
      "drift_start_cycle": 3,
      "agent_profiles": {
        "rule_engine": 0.25,
        "ml_scorer": 0.35,
        "ensemble": 0.4
      }
    },
    "final_state": {
      "trust_scores": {
        "rule_engine": 1.0,
        "ml_scorer": 1.0,
        "ensemble": 0.86
      },
      "trust_threshold": 0.5575,
      "suppression_threshold": 0.78,
      "drift_threshold_final": 0.95
    },
    "timeline": [
      {
        "cycle": 0,
        "phase": "RAMP-UP (mixed transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 0.96,
          "ml_scorer": 0.92,
          "ensemble": 0.92
        },
        "trust_threshold": 0.765,
        "suppression_threshold": 0.825,
        "drift_threshold": 0.4,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 1,
        "false_positives": 5,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 1,
        "phase": "RAMP-UP (mixed transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 0.98,
          "ml_scorer": 0.98,
          "ensemble": 1.0
        },
        "trust_threshold": 0.75,
        "suppression_threshold": 0.81,
        "drift_threshold": 0.4,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 1,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 2,
        "phase": "RAMP-UP (mixed transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.735,
        "suppression_threshold": 0.795,
        "drift_threshold": 0.4,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 1,
        "false_positives": 5,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 3,
        "phase": "RAMP-UP (mixed transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.72,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.44,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 2,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 4,
        "phase": "RAMP-UP (mixed transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.705,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.48,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 7,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 5,
        "phase": "RAMP-UP (mixed transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.69,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.52,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 4,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 6,
        "phase": "RAMP-UP (mixed transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.675,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.56,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 1,
        "false_positives": 6,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 7,
        "phase": "RAMP-UP (mixed transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.95
        },
        "trust_threshold": 0.6825,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.6,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_fraud": 1,
        "caught_fraud": 1,
        "false_positives": 6,
        "potential_loss": 438.44,
        "drift_agent_loss": 438.44,
        "drift_agent_missed": 1
      },
      {
        "cycle": 8,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.95
        },
        "trust_threshold": 0.69,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.64,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_fraud": 1,
        "caught_fraud": 1,
        "false_positives": 6,
        "potential_loss": 551.29,
        "drift_agent_loss": 551.29,
        "drift_agent_missed": 1
      },
      {
        "cycle": 9,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.99
        },
        "trust_threshold": 0.675,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.68,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 8,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 10,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.66,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.72,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 2,
        "false_positives": 6,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 11,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.645,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.76,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 8,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 12,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.85
        },
        "trust_threshold": 0.66,
        "suppression_threshold": 0.795,
        "drift_threshold": 0.8,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 5,
        "failures": 3,
        "missed_fraud": 3,
        "caught_fraud": 3,
        "false_positives": 2,
        "potential_loss": 559.51,
        "drift_agent_loss": 559.51,
        "drift_agent_missed": 3
      },
      {
        "cycle": 13,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.75
        },
        "trust_threshold": 0.675,
        "suppression_threshold": 0.81,
        "drift_threshold": 0.84,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 6,
        "failures": 2,
        "missed_fraud": 2,
        "caught_fraud": 1,
        "false_positives": 5,
        "potential_loss": 814.3100000000001,
        "drift_agent_loss": 814.3100000000001,
        "drift_agent_missed": 2
      },
      {
        "cycle": 14,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.75
        },
        "trust_threshold": 0.66,
        "suppression_threshold": 0.795,
        "drift_threshold": 0.88,
        "suppressed_agents": [
          "ensemble"
        ],
        "probation_agents": [
          "ensemble"
        ],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 1,
        "false_positives": 7,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 15,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.75
        },
        "trust_threshold": 0.645,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.92,
        "suppressed_agents": [
          "ensemble"
        ],
        "probation_agents": [
          "ensemble"
        ],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 3,
        "false_positives": 5,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 16,
        "phase": "STRESS (high-risk traffic)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.75
        },
        "trust_threshold": 0.63,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [
          "ensemble"
        ],
        "probation_agents": [
          "ensemble"
        ],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 2,
        "false_positives": 6,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 17,
        "phase": "RECOVERY (safe transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.79
        },
        "trust_threshold": 0.615,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [
          "ensemble"
        ],
        "probation_agents": [
          "ensemble"
        ],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 1,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 18,
        "phase": "RECOVERY (safe transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.81
        },
        "trust_threshold": 0.6,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 1,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 19,
        "phase": "RECOVERY (safe transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.87
        },
        "trust_threshold": 0.585,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 0,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 20,
        "phase": "RECOVERY (safe transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.91
        },
        "trust_threshold": 0.57,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 2,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 21,
        "phase": "RECOVERY (safe transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.555,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 2,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 22,
        "phase": "RECOVERY (safe transactions)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.55,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 2,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 23,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.55,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 3,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 24,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.55,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 3,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 25,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.55,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 4,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 26,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 1.0
        },
        "trust_threshold": 0.55,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 5,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      },
      {
        "cycle": 27,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.87
        },
        "trust_threshold": 0.565,
        "suppression_threshold": 0.795,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 5,
        "failures": 3,
        "missed_fraud": 3,
        "caught_fraud": 0,
        "false_positives": 3,
        "potential_loss": 997.76,
        "drift_agent_loss": 997.76,
        "drift_agent_missed": 3
      },
      {
        "cycle": 28,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.84
        },
        "trust_threshold": 0.5725,
        "suppression_threshold": 0.795,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_fraud": 1,
        "caught_fraud": 0,
        "false_positives": 3,
        "potential_loss": 151.17,
        "drift_agent_loss": 151.17,
        "drift_agent_missed": 1
      },
      {
        "cycle": 29,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "rule_engine": 1.0,
          "ml_scorer": 1.0,
          "ensemble": 0.86
        },
        "trust_threshold": 0.5575,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_fraud": 0,
        "caught_fraud": 0,
        "false_positives": 0,
        "potential_loss": 0,
        "drift_agent_loss": 0,
        "drift_agent_missed": 0
      }
    ]
  },
  "readmission": {
    "config": {
      "num_cycles": 30,
      "batch_size": 8,
      "routing_mode": "competitive",
      "data_source": "Synthetic (UCI Diabetes 130 distributions)",
      "drift_agent": "rapid_screen",
      "drift_rate": 0.04,
      "drift_start_cycle": 3,
      "penalty_per_readmission": 15200,
      "agent_profiles": {
        "conservative": 0.25,
        "predictive": 0.35,
        "rapid_screen": 0.4
      }
    },
    "final_state": {
      "trust_scores": {
        "conservative": 1.0,
        "predictive": 1.0,
        "rapid_screen": 0.94
      },
      "trust_threshold": 0.656,
      "suppression_threshold": 0.78,
      "drift_threshold_final": 0.95
    },
    "timeline": [
      {
        "cycle": 0,
        "phase": "RAMP-UP (mixed patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.92,
          "predictive": 0.92,
          "rapid_screen": 0.96
        },
        "trust_threshold": 0.788,
        "suppression_threshold": 0.848,
        "drift_threshold": 0.4,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 3,
        "unnecessary_flags": 2,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 1,
        "phase": "RAMP-UP (mixed patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.98,
          "predictive": 1.0,
          "rapid_screen": 0.98
        },
        "trust_threshold": 0.776,
        "suppression_threshold": 0.836,
        "drift_threshold": 0.4,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 1,
        "unnecessary_flags": 3,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 2,
        "phase": "RAMP-UP (mixed patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 1.0
        },
        "trust_threshold": 0.764,
        "suppression_threshold": 0.824,
        "drift_threshold": 0.4,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 2,
        "unnecessary_flags": 3,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 3,
        "phase": "RAMP-UP (mixed patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 1.0
        },
        "trust_threshold": 0.752,
        "suppression_threshold": 0.812,
        "drift_threshold": 0.44,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 1,
        "unnecessary_flags": 2,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 4,
        "phase": "RAMP-UP (mixed patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 1.0
        },
        "trust_threshold": 0.74,
        "suppression_threshold": 0.8,
        "drift_threshold": 0.48,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 1,
        "unnecessary_flags": 3,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 5,
        "phase": "RAMP-UP (mixed patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 1.0
        },
        "trust_threshold": 0.728,
        "suppression_threshold": 0.788,
        "drift_threshold": 0.52,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 2,
        "unnecessary_flags": 2,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 6,
        "phase": "RAMP-UP (mixed patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 1.0
        },
        "trust_threshold": 0.716,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.56,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 1,
        "unnecessary_flags": 7,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 7,
        "phase": "RAMP-UP (mixed patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 1.0
        },
        "trust_threshold": 0.704,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.6,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 3,
        "unnecessary_flags": 5,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 8,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.95
        },
        "trust_threshold": 0.71,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.64,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_readmissions": 1,
        "caught_readmissions": 1,
        "unnecessary_flags": 6,
        "penalty_incurred": 15200,
        "drift_agent_missed": 1,
        "drift_agent_penalty": 15200
      },
      {
        "cycle": 9,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.87
        },
        "trust_threshold": 0.722,
        "suppression_threshold": 0.792,
        "drift_threshold": 0.68,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 6,
        "failures": 2,
        "missed_readmissions": 2,
        "caught_readmissions": 4,
        "unnecessary_flags": 2,
        "penalty_incurred": 30400,
        "drift_agent_missed": 2,
        "drift_agent_penalty": 30400
      },
      {
        "cycle": 10,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.86
        },
        "trust_threshold": 0.728,
        "suppression_threshold": 0.792,
        "drift_threshold": 0.72,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_readmissions": 1,
        "caught_readmissions": 3,
        "unnecessary_flags": 2,
        "penalty_incurred": 15200,
        "drift_agent_missed": 1,
        "drift_agent_penalty": 15200
      },
      {
        "cycle": 11,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.78
        },
        "trust_threshold": 0.74,
        "suppression_threshold": 0.804,
        "drift_threshold": 0.76,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 6,
        "failures": 2,
        "missed_readmissions": 2,
        "caught_readmissions": 0,
        "unnecessary_flags": 5,
        "penalty_incurred": 30400,
        "drift_agent_missed": 2,
        "drift_agent_penalty": 30400
      },
      {
        "cycle": 12,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.78
        },
        "trust_threshold": 0.728,
        "suppression_threshold": 0.792,
        "drift_threshold": 0.8,
        "suppressed_agents": [
          "rapid_screen"
        ],
        "probation_agents": [
          "rapid_screen"
        ],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 3,
        "unnecessary_flags": 5,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 13,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.78
        },
        "trust_threshold": 0.716,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.84,
        "suppressed_agents": [
          "rapid_screen"
        ],
        "probation_agents": [
          "rapid_screen"
        ],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 3,
        "unnecessary_flags": 5,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 14,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.73
        },
        "trust_threshold": 0.722,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.88,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_readmissions": 1,
        "caught_readmissions": 3,
        "unnecessary_flags": 4,
        "penalty_incurred": 15200,
        "drift_agent_missed": 1,
        "drift_agent_penalty": 15200
      },
      {
        "cycle": 15,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.73
        },
        "trust_threshold": 0.71,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.92,
        "suppressed_agents": [
          "rapid_screen"
        ],
        "probation_agents": [
          "rapid_screen"
        ],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 2,
        "unnecessary_flags": 6,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 16,
        "phase": "STRESS (high-risk elderly)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.73
        },
        "trust_threshold": 0.698,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [
          "rapid_screen"
        ],
        "probation_agents": [
          "rapid_screen"
        ],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 0,
        "unnecessary_flags": 8,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 17,
        "phase": "RECOVERY (low-risk patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.77
        },
        "trust_threshold": 0.686,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [
          "rapid_screen"
        ],
        "probation_agents": [
          "rapid_screen"
        ],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 0,
        "unnecessary_flags": 1,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 18,
        "phase": "RECOVERY (low-risk patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 0.95,
          "rapid_screen": 0.81
        },
        "trust_threshold": 0.692,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [
          "rapid_screen"
        ],
        "probation_agents": [
          "rapid_screen"
        ],
        "successes": 7,
        "failures": 1,
        "missed_readmissions": 1,
        "caught_readmissions": 0,
        "unnecessary_flags": 0,
        "penalty_incurred": 15200,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 19,
        "phase": "RECOVERY (low-risk patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.87
        },
        "trust_threshold": 0.68,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 0,
        "unnecessary_flags": 0,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 20,
        "phase": "RECOVERY (low-risk patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.87
        },
        "trust_threshold": 0.668,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 0,
        "unnecessary_flags": 0,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 21,
        "phase": "RECOVERY (low-risk patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.95
        },
        "trust_threshold": 0.656,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 0,
        "unnecessary_flags": 0,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 22,
        "phase": "RECOVERY (low-risk patients)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 0.99,
          "rapid_screen": 0.94
        },
        "trust_threshold": 0.668,
        "suppression_threshold": 0.792,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 6,
        "failures": 2,
        "missed_readmissions": 2,
        "caught_readmissions": 1,
        "unnecessary_flags": 1,
        "penalty_incurred": 30400,
        "drift_agent_missed": 1,
        "drift_agent_penalty": 15200
      },
      {
        "cycle": 23,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.89
        },
        "trust_threshold": 0.674,
        "suppression_threshold": 0.792,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_readmissions": 1,
        "caught_readmissions": 0,
        "unnecessary_flags": 2,
        "penalty_incurred": 15200,
        "drift_agent_missed": 1,
        "drift_agent_penalty": 15200
      },
      {
        "cycle": 24,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.93
        },
        "trust_threshold": 0.662,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 1,
        "unnecessary_flags": 3,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 25,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 0.95,
          "predictive": 1.0,
          "rapid_screen": 0.97
        },
        "trust_threshold": 0.668,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_readmissions": 1,
        "caught_readmissions": 1,
        "unnecessary_flags": 2,
        "penalty_incurred": 15200,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 26,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.99
        },
        "trust_threshold": 0.656,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 0,
        "unnecessary_flags": 4,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 27,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 1.0
        },
        "trust_threshold": 0.644,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 8,
        "failures": 0,
        "missed_readmissions": 0,
        "caught_readmissions": 2,
        "unnecessary_flags": 3,
        "penalty_incurred": 0,
        "drift_agent_missed": 0,
        "drift_agent_penalty": 0
      },
      {
        "cycle": 28,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.97
        },
        "trust_threshold": 0.65,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_readmissions": 1,
        "caught_readmissions": 0,
        "unnecessary_flags": 2,
        "penalty_incurred": 15200,
        "drift_agent_missed": 1,
        "drift_agent_penalty": 15200
      },
      {
        "cycle": 29,
        "phase": "STEADY STATE (mixed)",
        "status": "executed",
        "trust_scores": {
          "conservative": 1.0,
          "predictive": 1.0,
          "rapid_screen": 0.94
        },
        "trust_threshold": 0.656,
        "suppression_threshold": 0.78,
        "drift_threshold": 0.95,
        "suppressed_agents": [],
        "probation_agents": [],
        "successes": 7,
        "failures": 1,
        "missed_readmissions": 1,
        "caught_readmissions": 1,
        "unnecessary_flags": 3,
        "penalty_incurred": 15200,
        "drift_agent_missed": 1,
        "drift_agent_penalty": 15200
      }
    ]
  }
} as Record<DomainId, DemoDataset>;
