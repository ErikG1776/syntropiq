"""
Loan Application Data Generator

Produces realistic loan applications modeled on Lending Club distributions.
Each loan has a known outcome (defaulted or not) based on probability curves
derived from real default rates by grade.

Can also load a real Lending Club CSV (curated via prepare_data.py) and
serve loans in phase-appropriate batches for the governance demo.
"""

import csv
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from syntropiq.core.models import Task

# Path to the curated sample (created by prepare_data.py)
SAMPLE_CSV_PATH = Path(__file__).parent / "data" / "lending_club_sample.csv"


@dataclass
class LoanApplication:
    """A single loan application with known outcome."""
    loan_id: str
    amount: float
    term_months: int
    interest_rate: float
    grade: str            # A through G
    sub_grade: str        # A1-G5
    annual_income: float
    dti: float            # debt-to-income ratio
    purpose: str
    home_ownership: str
    defaulted: bool       # ground truth outcome

    @property
    def risk_score(self) -> float:
        """
        Composite risk score [0.0, 1.0] derived from loan features.
        Higher = riskier.
        """
        grade_risk = {"A": 0.1, "B": 0.2, "C": 0.35, "D": 0.5,
                      "E": 0.65, "F": 0.8, "G": 0.9}
        base = grade_risk.get(self.grade, 0.5)

        # DTI contribution (high DTI = more risk)
        dti_factor = min(self.dti / 40.0, 1.0) * 0.15

        # Amount contribution (larger loans = marginal risk increase)
        amount_factor = min(self.amount / 40000.0, 1.0) * 0.1

        # Interest rate as risk signal
        rate_factor = min(self.interest_rate / 30.0, 1.0) * 0.1

        return min(1.0, base + dti_factor + amount_factor + rate_factor)

    def to_task(self) -> Task:
        """Convert to a Syntropiq Task for governance processing."""
        risk = self.risk_score
        # Impact scales with loan amount
        impact = min(1.0, self.amount / 35000.0)
        # Urgency is moderate for all loans (they're queued)
        urgency = 0.6

        return Task(
            id=self.loan_id,
            impact=round(impact, 3),
            urgency=urgency,
            risk=round(risk, 3),
            metadata={
                "amount": self.amount,
                "grade": self.grade,
                "sub_grade": self.sub_grade,
                "interest_rate": self.interest_rate,
                "dti": self.dti,
                "annual_income": self.annual_income,
                "purpose": self.purpose,
                "home_ownership": self.home_ownership,
                "defaulted": self.defaulted,
                "term_months": self.term_months,
            }
        )


# ── Default rate curves (modeled on Lending Club actuals) ────

# Real Lending Club default rates by grade (approximate):
# A: 5-7%, B: 11-14%, C: 17-21%, D: 24-28%, E: 31-36%, F: 38-45%, G: 45-55%
DEFAULT_RATES = {
    "A": 0.06, "B": 0.13, "C": 0.19, "D": 0.26,
    "E": 0.34, "F": 0.42, "G": 0.50,
}

GRADE_DISTRIBUTION = {
    "A": 0.18, "B": 0.28, "C": 0.24, "D": 0.15,
    "E": 0.09, "F": 0.04, "G": 0.02,
}

PURPOSES = [
    "debt_consolidation", "credit_card", "home_improvement",
    "major_purchase", "medical", "car", "small_business",
    "moving", "vacation", "wedding",
]

OWNERSHIPS = ["RENT", "MORTGAGE", "OWN"]


def _pick_grade(rng: random.Random) -> str:
    """Weighted random grade selection."""
    r = rng.random()
    cumulative = 0.0
    for grade, prob in GRADE_DISTRIBUTION.items():
        cumulative += prob
        if r <= cumulative:
            return grade
    return "C"


def _generate_loan(loan_id: str, rng: random.Random) -> LoanApplication:
    """Generate a single realistic loan application."""
    grade = _pick_grade(rng)
    sub_idx = rng.randint(1, 5)
    sub_grade = f"{grade}{sub_idx}"

    # Interest rate ranges by grade
    rate_ranges = {
        "A": (5.0, 8.0), "B": (8.0, 12.0), "C": (12.0, 16.0),
        "D": (16.0, 21.0), "E": (21.0, 25.0), "F": (25.0, 28.0),
        "G": (28.0, 31.0),
    }
    lo, hi = rate_ranges[grade]
    interest_rate = round(rng.uniform(lo, hi), 2)

    # Loan amount (roughly lognormal, capped)
    amount = round(min(40000, max(1000, rng.lognormvariate(9.2, 0.7))), 0)

    term = rng.choice([36, 60])

    # Income (lognormal)
    annual_income = round(max(20000, rng.lognormvariate(11.0, 0.6)), 0)

    # DTI: higher grades tend to have lower DTI
    grade_dti_base = {"A": 10, "B": 14, "C": 18, "D": 22,
                      "E": 25, "F": 28, "G": 30}
    dti = round(max(0, rng.gauss(grade_dti_base[grade], 6)), 1)

    purpose = rng.choice(PURPOSES)
    ownership = rng.choices(OWNERSHIPS, weights=[0.4, 0.45, 0.15])[0]

    # Default outcome based on grade default rate
    defaulted = rng.random() < DEFAULT_RATES[grade]

    return LoanApplication(
        loan_id=loan_id,
        amount=amount,
        term_months=term,
        interest_rate=interest_rate,
        grade=grade,
        sub_grade=sub_grade,
        annual_income=annual_income,
        dti=dti,
        purpose=purpose,
        home_ownership=ownership,
        defaulted=defaulted,
    )


def generate_loan_batch(
    batch_size: int = 10,
    batch_id: int = 0,
    seed: Optional[int] = None,
    risk_profile: str = "mixed",
) -> List[LoanApplication]:
    """
    Generate a batch of realistic loan applications.

    Args:
        batch_size: Number of loans per batch
        batch_id: Batch identifier (used in loan IDs)
        seed: Random seed for reproducibility
        risk_profile: "mixed" (normal distribution), "high_risk" (D-G heavy),
                      or "low_risk" (A-B heavy)
    """
    rng = random.Random(seed if seed is not None else batch_id)

    if risk_profile == "high_risk":
        return [
            _generate_high_risk_loan(f"LOAN_{batch_id:03d}_{i:03d}", rng)
            for i in range(batch_size)
        ]
    elif risk_profile == "low_risk":
        return [
            _generate_low_risk_loan(f"LOAN_{batch_id:03d}_{i:03d}", rng)
            for i in range(batch_size)
        ]

    return [
        _generate_loan(f"LOAN_{batch_id:03d}_{i:03d}", rng)
        for i in range(batch_size)
    ]


def _generate_high_risk_loan(loan_id: str, rng: random.Random) -> LoanApplication:
    """
    Generate a high-risk loan (Grade C-G).
    These are the loans a drifting agent will approve that shouldn't be approved.
    """
    grade = rng.choices(
        ["C", "D", "E", "F", "G"],
        weights=[0.25, 0.30, 0.25, 0.12, 0.08],
    )[0]
    return _generate_loan_with_grade(loan_id, grade, rng)


def _generate_low_risk_loan(loan_id: str, rng: random.Random) -> LoanApplication:
    """Generate a low-risk loan (Grade A-B) for redemption phases."""
    grade = rng.choices(["A", "B"], weights=[0.5, 0.5])[0]
    return _generate_loan_with_grade(loan_id, grade, rng)


def _generate_loan_with_grade(
    loan_id: str, grade: str, rng: random.Random
) -> LoanApplication:
    """Generate a loan for a specific grade."""
    sub_idx = rng.randint(1, 5)
    sub_grade = f"{grade}{sub_idx}"

    rate_ranges = {
        "A": (5.0, 8.0), "B": (8.0, 12.0), "C": (12.0, 16.0),
        "D": (16.0, 21.0), "E": (21.0, 25.0), "F": (25.0, 28.0),
        "G": (28.0, 31.0),
    }
    lo, hi = rate_ranges[grade]
    interest_rate = round(rng.uniform(lo, hi), 2)
    amount = round(min(40000, max(1000, rng.lognormvariate(9.2, 0.7))), 0)
    term = rng.choice([36, 60])
    annual_income = round(max(20000, rng.lognormvariate(11.0, 0.6)), 0)
    grade_dti_base = {"A": 10, "B": 14, "C": 18, "D": 22,
                      "E": 25, "F": 28, "G": 30}
    dti = round(max(0, rng.gauss(grade_dti_base[grade], 6)), 1)
    purpose = rng.choice(PURPOSES)
    ownership = rng.choices(OWNERSHIPS, weights=[0.4, 0.45, 0.15])[0]
    defaulted = rng.random() < DEFAULT_RATES[grade]

    return LoanApplication(
        loan_id=loan_id, amount=amount, term_months=term,
        interest_rate=interest_rate, grade=grade, sub_grade=sub_grade,
        annual_income=annual_income, dti=dti, purpose=purpose,
        home_ownership=ownership, defaulted=defaulted,
    )


def load_lending_club_csv(
    csv_path: str,
    max_rows: int = 5000,
) -> List[LoanApplication]:
    """
    Load real Lending Club data from CSV.

    Expected columns: loan_amnt, term, int_rate, grade, sub_grade,
    annual_inc, dti, purpose, home_ownership, loan_status

    Args:
        csv_path: Path to Lending Club CSV file
        max_rows: Maximum rows to load
    """
    loans = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            try:
                # Parse loan_status to defaulted boolean
                status = row.get("loan_status", "").strip()
                if status in ("Charged Off", "Default"):
                    defaulted = True
                elif status in ("Fully Paid", "Current"):
                    defaulted = False
                else:
                    continue  # skip ambiguous statuses

                # Parse interest rate (may have % sign)
                rate_str = row.get("int_rate", "0").replace("%", "").strip()

                # Parse term (may be " 36 months" or "36")
                term_str = row.get("term", "36").strip().split()[0]

                loan = LoanApplication(
                    loan_id=f"LC_{i:06d}",
                    amount=float(row.get("loan_amnt", 0)),
                    term_months=int(term_str),
                    interest_rate=float(rate_str),
                    grade=row.get("grade", "C").strip(),
                    sub_grade=row.get("sub_grade", "C1").strip(),
                    annual_income=float(row.get("annual_inc", 50000)),
                    dti=float(row.get("dti", 15) or 15),
                    purpose=row.get("purpose", "other").strip(),
                    home_ownership=row.get("home_ownership", "RENT").strip(),
                    defaulted=defaulted,
                )
                loans.append(loan)
            except (ValueError, KeyError):
                continue

    return loans


# ── Real Data Pool ───────────────────────────────────────────

# Grade tiers for phase-based sampling
_SAFE_GRADES = {"A", "B"}
_RISKY_GRADES = {"C", "D", "E", "F", "G"}


class RealDataPool:
    """
    Pool of real Lending Club loans that serves phase-appropriate batches.

    Loads the curated sample CSV (from prepare_data.py) and indexes loans
    by grade. Each call to sample_batch() draws loans matching the
    requested risk profile, without replacement.

    This is what makes the real-data demo work: the same phase structure
    (ramp-up → stress → recovery → steady) but with actual loan outcomes
    instead of synthetic probabilities.
    """

    def __init__(self, csv_path: str = None, seed: int = 42):
        """
        Args:
            csv_path: Path to curated LC CSV. Defaults to bundled sample.
            seed: Random seed for reproducible batch sampling.
        """
        self.csv_path = csv_path or str(SAMPLE_CSV_PATH)
        self.rng = random.Random(seed)

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"No curated data at: {self.csv_path}\n"
                f"Run: python -m syntropiq.demo.lending.prepare_data <raw_lc.csv>"
            )

        # Load all loans
        all_loans = load_lending_club_csv(self.csv_path, max_rows=10000)
        if not all_loans:
            raise ValueError(f"No valid loans in: {self.csv_path}")

        # Index by risk tier
        self._safe = [l for l in all_loans if l.grade in _SAFE_GRADES]
        self._risky = [l for l in all_loans if l.grade in _RISKY_GRADES]
        self._mixed = list(all_loans)

        # Shuffle each pool for varied sampling
        self.rng.shuffle(self._safe)
        self.rng.shuffle(self._risky)
        self.rng.shuffle(self._mixed)

        # Cursors for round-robin sampling (no replacement within a pass)
        self._safe_idx = 0
        self._risky_idx = 0
        self._mixed_idx = 0

        # Stats
        self.total_loans = len(all_loans)
        self.total_defaults = sum(1 for l in all_loans if l.defaulted)
        self.default_rate = self.total_defaults / self.total_loans

    def sample_batch(
        self,
        batch_size: int,
        batch_id: int,
        risk_profile: str = "mixed",
    ) -> List[LoanApplication]:
        """
        Draw a batch of real loans matching the risk profile.

        Args:
            batch_size: Number of loans to return.
            batch_id: Used for loan ID prefix.
            risk_profile: "mixed", "high_risk", or "low_risk"

        Returns:
            List of LoanApplication with real outcomes and re-stamped IDs.
        """
        if risk_profile == "high_risk":
            pool, cursor_attr = self._risky, "_risky_idx"
        elif risk_profile == "low_risk":
            pool, cursor_attr = self._safe, "_safe_idx"
        else:
            pool, cursor_attr = self._mixed, "_mixed_idx"

        if not pool:
            # Fallback: use mixed pool if a tier is empty
            pool, cursor_attr = self._mixed, "_mixed_idx"

        cursor = getattr(self, cursor_attr)
        batch = []

        for i in range(batch_size):
            if cursor >= len(pool):
                # Wrap around — re-shuffle for variety
                self.rng.shuffle(pool)
                cursor = 0

            loan = pool[cursor]
            cursor += 1

            # Re-stamp ID to match demo format while preserving all real data
            batch.append(LoanApplication(
                loan_id=f"LC_{batch_id:03d}_{i:03d}",
                amount=loan.amount,
                term_months=loan.term_months,
                interest_rate=loan.interest_rate,
                grade=loan.grade,
                sub_grade=loan.sub_grade,
                annual_income=loan.annual_income,
                dti=loan.dti,
                purpose=loan.purpose,
                home_ownership=loan.home_ownership,
                defaulted=loan.defaulted,
            ))

        setattr(self, cursor_attr, cursor)
        return batch

    @property
    def description(self) -> str:
        """Human-readable data source label for demo output."""
        return (
            f"Lending Club ({self.total_loans:,} real loans, "
            f"{self.default_rate:.1%} default rate)"
        )

    @staticmethod
    def is_available(csv_path: str = None) -> bool:
        """Check if curated real data exists."""
        path = csv_path or str(SAMPLE_CSV_PATH)
        return os.path.exists(path)
