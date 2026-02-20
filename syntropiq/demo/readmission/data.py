"""
Hospital Readmission Data Generator

Produces realistic patient discharge encounters modeled on the UCI Diabetes
130-US Hospitals dataset distributions.  Each encounter has a known outcome
(readmitted_30d) based on probability curves derived from real readmission
rates by risk tier.

Can also load a real UCI CSV (curated via prepare_data.py) and serve
encounters in phase-appropriate batches for the governance demo.
"""

import csv
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from syntropiq.core.models import Task

# Path to the curated sample (created by prepare_data.py)
SAMPLE_CSV_PATH = Path(__file__).parent / "data" / "diabetes_readmission_sample.csv"


@dataclass
class PatientEncounter:
    """A single hospital discharge encounter with known readmission outcome."""
    encounter_id: str
    age_group: str           # [0-10), [10-20), ... [90-100)
    time_in_hospital: int    # 1-14 days
    num_medications: int     # 1-81
    num_diagnoses: int       # 1-16
    num_lab_procedures: int  # 1-132
    a1c_result: str          # None, Norm, >7, >8
    insulin: str             # No, Steady, Up, Down
    prior_inpatient: int     # 0-21 prior inpatient visits
    prior_emergency: int     # 0-76 prior emergency visits
    discharge_disposition: str  # Home, SNF, other
    risk_tier: str           # R1 through R5
    readmitted_30d: bool     # ground truth: readmitted within 30 days

    @property
    def risk_score(self) -> float:
        """
        Composite readmission risk score [0.0, 1.0] derived from clinical features.
        Higher = more likely to be readmitted.
        """
        tier_risk = {
            "R1": 0.08, "R2": 0.22, "R3": 0.40, "R4": 0.60, "R5": 0.82,
        }
        base = tier_risk.get(self.risk_tier, 0.35)

        # Age contribution (elderly = higher risk)
        age_factor = 0.0
        if self.age_group in ("[70-80)", "[80-90)", "[90-100)"):
            age_factor = 0.10
        elif self.age_group in ("[60-70)",):
            age_factor = 0.05

        # HbA1c contribution (abnormal = higher risk)
        a1c_factor = {"None": 0.0, "Norm": 0.0, ">7": 0.06, ">8": 0.10}
        a1c = a1c_factor.get(self.a1c_result, 0.0)

        # Prior visits contribution (recidivism signal)
        prior_factor = min(self.prior_inpatient * 0.02, 0.08)

        # Medication complexity
        med_factor = min(self.num_medications / 80.0 * 0.06, 0.06)

        return min(1.0, base + age_factor + a1c + prior_factor + med_factor)

    def to_task(self) -> Task:
        """Convert to a Syntropiq Task for governance processing."""
        risk = self.risk_score
        # Impact: each missed readmission costs ~$15,200 in Medicare penalties
        # Scale by clinical complexity
        complexity = min(1.0, (self.num_diagnoses / 16 + self.num_medications / 40) / 2)
        impact = max(0.3, complexity)
        # Hospital discharge planning is time-sensitive but not real-time
        urgency = 0.75

        return Task(
            id=self.encounter_id,
            impact=round(impact, 3),
            urgency=urgency,
            risk=round(risk, 3),
            metadata={
                "age_group": self.age_group,
                "time_in_hospital": self.time_in_hospital,
                "num_medications": self.num_medications,
                "num_diagnoses": self.num_diagnoses,
                "num_lab_procedures": self.num_lab_procedures,
                "a1c_result": self.a1c_result,
                "insulin": self.insulin,
                "prior_inpatient": self.prior_inpatient,
                "prior_emergency": self.prior_emergency,
                "discharge_disposition": self.discharge_disposition,
                "risk_tier": self.risk_tier,
                "readmitted_30d": self.readmitted_30d,
            },
        )


# ── Readmission rate curves (modeled on UCI Diabetes dataset analysis) ──

# Real readmission rates from UCI data:
#   Overall 30-day readmission: 11.2%
#   Elderly + high A1c + prior visits: 25-40%
#   Young + normal A1c + no prior visits: 3-5%
READMISSION_RATES = {
    "R1": 0.03, "R2": 0.08, "R3": 0.15,
    "R4": 0.25, "R5": 0.40,
}

TIER_DISTRIBUTION = {
    "R1": 0.25, "R2": 0.30, "R3": 0.22,
    "R4": 0.14, "R5": 0.09,
}

AGE_GROUPS = [
    "[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)",
    "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)",
]

# Age distribution weights by risk tier
AGE_WEIGHTS_BY_TIER = {
    "R1": [0.01, 0.02, 0.10, 0.20, 0.30, 0.25, 0.08, 0.03, 0.01, 0.00],
    "R2": [0.01, 0.01, 0.05, 0.10, 0.20, 0.30, 0.20, 0.08, 0.04, 0.01],
    "R3": [0.00, 0.01, 0.03, 0.05, 0.12, 0.22, 0.28, 0.18, 0.08, 0.03],
    "R4": [0.00, 0.00, 0.01, 0.03, 0.06, 0.15, 0.25, 0.28, 0.16, 0.06],
    "R5": [0.00, 0.00, 0.01, 0.02, 0.04, 0.10, 0.18, 0.30, 0.25, 0.10],
}

A1C_RESULTS = ["None", "Norm", ">7", ">8"]
A1C_WEIGHTS_BY_TIER = {
    "R1": [0.85, 0.10, 0.03, 0.02],
    "R2": [0.82, 0.08, 0.06, 0.04],
    "R3": [0.78, 0.06, 0.08, 0.08],
    "R4": [0.70, 0.05, 0.10, 0.15],
    "R5": [0.60, 0.04, 0.12, 0.24],
}

INSULIN_OPTIONS = ["No", "Steady", "Up", "Down"]
INSULIN_WEIGHTS_BY_TIER = {
    "R1": [0.70, 0.18, 0.06, 0.06],
    "R2": [0.50, 0.28, 0.12, 0.10],
    "R3": [0.38, 0.32, 0.16, 0.14],
    "R4": [0.28, 0.35, 0.20, 0.17],
    "R5": [0.20, 0.32, 0.26, 0.22],
}

DISCHARGE_OPTIONS = ["Home", "SNF", "Home Health", "Other"]
DISCHARGE_WEIGHTS_BY_TIER = {
    "R1": [0.80, 0.02, 0.12, 0.06],
    "R2": [0.70, 0.05, 0.16, 0.09],
    "R3": [0.55, 0.12, 0.22, 0.11],
    "R4": [0.40, 0.22, 0.25, 0.13],
    "R5": [0.28, 0.32, 0.26, 0.14],
}


def _pick_tier(rng: random.Random) -> str:
    """Weighted random tier selection."""
    r = rng.random()
    cumulative = 0.0
    for tier, prob in TIER_DISTRIBUTION.items():
        cumulative += prob
        if r <= cumulative:
            return tier
    return "R2"


def _generate_encounter(
    enc_id: str, rng: random.Random, tier: Optional[str] = None,
) -> PatientEncounter:
    """Generate a single realistic patient encounter."""
    if tier is None:
        tier = _pick_tier(rng)

    age_group = rng.choices(AGE_GROUPS, weights=AGE_WEIGHTS_BY_TIER[tier])[0]
    a1c_result = rng.choices(A1C_RESULTS, weights=A1C_WEIGHTS_BY_TIER[tier])[0]
    insulin = rng.choices(INSULIN_OPTIONS, weights=INSULIN_WEIGHTS_BY_TIER[tier])[0]
    discharge = rng.choices(DISCHARGE_OPTIONS, weights=DISCHARGE_WEIGHTS_BY_TIER[tier])[0]

    # Time in hospital: higher tiers = longer stays
    time_base = {"R1": 2.5, "R2": 3.5, "R3": 4.5, "R4": 6.0, "R5": 7.5}
    time_in_hospital = max(1, min(14, int(rng.gauss(time_base[tier], 1.8))))

    # Number of medications: correlated with tier
    med_base = {"R1": 8, "R2": 13, "R3": 18, "R4": 24, "R5": 32}
    num_medications = max(1, min(81, int(rng.gauss(med_base[tier], 5))))

    # Number of diagnoses: higher tiers = more comorbidities
    diag_base = {"R1": 4, "R2": 6, "R3": 8, "R4": 10, "R5": 13}
    num_diagnoses = max(1, min(16, int(rng.gauss(diag_base[tier], 2))))

    # Lab procedures
    lab_base = {"R1": 30, "R2": 40, "R3": 50, "R4": 55, "R5": 60}
    num_lab_procedures = max(1, min(132, int(rng.gauss(lab_base[tier], 12))))

    # Prior inpatient visits (strong readmission predictor)
    prior_base = {"R1": 0.1, "R2": 0.3, "R3": 0.8, "R4": 1.5, "R5": 3.0}
    prior_inpatient = max(0, min(21, int(rng.expovariate(1.0 / max(0.01, prior_base[tier])))))

    # Prior emergency visits
    er_base = {"R1": 0.1, "R2": 0.2, "R3": 0.4, "R4": 0.7, "R5": 1.2}
    prior_emergency = max(0, min(76, int(rng.expovariate(1.0 / max(0.01, er_base[tier])))))

    # Readmission outcome based on tier
    readmitted_30d = rng.random() < READMISSION_RATES[tier]

    return PatientEncounter(
        encounter_id=enc_id,
        age_group=age_group,
        time_in_hospital=time_in_hospital,
        num_medications=num_medications,
        num_diagnoses=num_diagnoses,
        num_lab_procedures=num_lab_procedures,
        a1c_result=a1c_result,
        insulin=insulin,
        prior_inpatient=prior_inpatient,
        prior_emergency=prior_emergency,
        discharge_disposition=discharge,
        risk_tier=tier,
        readmitted_30d=readmitted_30d,
    )


def generate_encounter_batch(
    batch_size: int = 10,
    batch_id: int = 0,
    seed: Optional[int] = None,
    risk_profile: str = "mixed",
) -> List[PatientEncounter]:
    """
    Generate a batch of realistic patient encounters.

    Args:
        batch_size: Number of encounters per batch
        batch_id: Batch identifier (used in encounter IDs)
        seed: Random seed for reproducibility
        risk_profile: "mixed" (normal), "high_risk" (R3-R5 heavy),
                      or "low_risk" (R1-R2 heavy)
    """
    rng = random.Random(seed if seed is not None else batch_id)

    if risk_profile == "high_risk":
        return [
            _generate_high_risk_encounter(f"ENC_{batch_id:03d}_{i:03d}", rng)
            for i in range(batch_size)
        ]
    elif risk_profile == "low_risk":
        return [
            _generate_low_risk_encounter(f"ENC_{batch_id:03d}_{i:03d}", rng)
            for i in range(batch_size)
        ]

    return [
        _generate_encounter(f"ENC_{batch_id:03d}_{i:03d}", rng)
        for i in range(batch_size)
    ]


def _generate_high_risk_encounter(
    enc_id: str, rng: random.Random,
) -> PatientEncounter:
    """
    Generate a high-risk encounter (R3-R5).
    These are the patients a drifting agent will discharge without follow-up.
    """
    tier = rng.choices(
        ["R3", "R4", "R5"],
        weights=[0.35, 0.40, 0.25],
    )[0]
    return _generate_encounter(enc_id, rng, tier=tier)


def _generate_low_risk_encounter(
    enc_id: str, rng: random.Random,
) -> PatientEncounter:
    """Generate a low-risk encounter (R1-R2) for redemption phases."""
    tier = rng.choices(["R1", "R2"], weights=[0.55, 0.45])[0]
    return _generate_encounter(enc_id, rng, tier=tier)


def load_readmission_csv(
    csv_path: str,
    max_rows: int = 5000,
) -> List[PatientEncounter]:
    """
    Load curated readmission data from CSV.

    Expected columns: encounter_id, age_group, time_in_hospital,
    num_medications, num_diagnoses, num_lab_procedures, a1c_result,
    insulin, prior_inpatient, prior_emergency, discharge_disposition,
    risk_tier, readmitted_30d

    Args:
        csv_path: Path to curated CSV file
        max_rows: Maximum rows to load
    """
    encounters = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            try:
                readmitted_raw = row.get("readmitted_30d", "0").strip()
                readmitted = readmitted_raw in ("1", "True", "true", "yes")

                enc = PatientEncounter(
                    encounter_id=f"UCI_{i:06d}",
                    age_group=row.get("age_group", "[50-60)").strip(),
                    time_in_hospital=int(row.get("time_in_hospital", 4)),
                    num_medications=int(row.get("num_medications", 15)),
                    num_diagnoses=int(row.get("num_diagnoses", 7)),
                    num_lab_procedures=int(row.get("num_lab_procedures", 44)),
                    a1c_result=row.get("a1c_result", "None").strip(),
                    insulin=row.get("insulin", "No").strip(),
                    prior_inpatient=int(row.get("prior_inpatient", 0)),
                    prior_emergency=int(row.get("prior_emergency", 0)),
                    discharge_disposition=row.get("discharge_disposition", "Home").strip(),
                    risk_tier=row.get("risk_tier", "R2").strip(),
                    readmitted_30d=readmitted,
                )
                encounters.append(enc)
            except (ValueError, KeyError):
                continue

    return encounters


# ── Real Data Pool ───────────────────────────────────────────

# Tier groups for phase-based sampling
_SAFE_TIERS = {"R1", "R2"}
_RISKY_TIERS = {"R3", "R4", "R5"}


class RealDataPool:
    """
    Pool of real UCI patient encounters that serves phase-appropriate batches.

    Loads the curated sample CSV (from prepare_data.py) and indexes
    encounters by risk tier. Each call to sample_batch() draws
    encounters matching the requested risk profile, without replacement.
    """

    def __init__(self, csv_path: str = None, seed: int = 42):
        self.csv_path = csv_path or str(SAMPLE_CSV_PATH)
        self.rng = random.Random(seed)

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"No curated data at: {self.csv_path}\n"
                f"Run: python -m syntropiq.demo.readmission.prepare_data "
                f"<diabetic_data.csv>"
            )

        all_encs = load_readmission_csv(self.csv_path, max_rows=10000)
        if not all_encs:
            raise ValueError(f"No valid encounters in: {self.csv_path}")

        # Index by risk tier
        self._safe = [e for e in all_encs if e.risk_tier in _SAFE_TIERS]
        self._risky = [e for e in all_encs if e.risk_tier in _RISKY_TIERS]
        self._mixed = list(all_encs)

        self.rng.shuffle(self._safe)
        self.rng.shuffle(self._risky)
        self.rng.shuffle(self._mixed)

        self._safe_idx = 0
        self._risky_idx = 0
        self._mixed_idx = 0

        self.total_encs = len(all_encs)
        self.total_readmitted = sum(1 for e in all_encs if e.readmitted_30d)
        self.readmission_rate = self.total_readmitted / self.total_encs

    def sample_batch(
        self,
        batch_size: int,
        batch_id: int,
        risk_profile: str = "mixed",
    ) -> List[PatientEncounter]:
        """Draw a batch of real encounters matching the risk profile."""
        if risk_profile == "high_risk":
            pool, cursor_attr = self._risky, "_risky_idx"
        elif risk_profile == "low_risk":
            pool, cursor_attr = self._safe, "_safe_idx"
        else:
            pool, cursor_attr = self._mixed, "_mixed_idx"

        if not pool:
            pool, cursor_attr = self._mixed, "_mixed_idx"

        cursor = getattr(self, cursor_attr)
        batch = []

        for i in range(batch_size):
            if cursor >= len(pool):
                self.rng.shuffle(pool)
                cursor = 0

            enc = pool[cursor]
            cursor += 1

            batch.append(PatientEncounter(
                encounter_id=f"UCI_{batch_id:03d}_{i:03d}",
                age_group=enc.age_group,
                time_in_hospital=enc.time_in_hospital,
                num_medications=enc.num_medications,
                num_diagnoses=enc.num_diagnoses,
                num_lab_procedures=enc.num_lab_procedures,
                a1c_result=enc.a1c_result,
                insulin=enc.insulin,
                prior_inpatient=enc.prior_inpatient,
                prior_emergency=enc.prior_emergency,
                discharge_disposition=enc.discharge_disposition,
                risk_tier=enc.risk_tier,
                readmitted_30d=enc.readmitted_30d,
            ))

        setattr(self, cursor_attr, cursor)
        return batch

    @property
    def description(self) -> str:
        return (
            f"UCI Diabetes 130 ({self.total_encs:,} real encounters, "
            f"{self.readmission_rate:.1%} readmission rate)"
        )

    @staticmethod
    def is_available(csv_path: str = None) -> bool:
        path = csv_path or str(SAMPLE_CSV_PATH)
        return os.path.exists(path)
