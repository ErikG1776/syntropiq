"""
Fraud Transaction Data Generator

Produces realistic payment transactions modeled on IEEE-CIS Fraud Detection
distributions.  Each transaction has a known outcome (is_fraud) based on
probability curves derived from real fraud rates by risk tier.

Can also load a real IEEE-CIS CSV (curated via prepare_data.py) and
serve transactions in phase-appropriate batches for the governance demo.
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
SAMPLE_CSV_PATH = Path(__file__).parent / "data" / "ieee_cis_sample.csv"


@dataclass
class FraudTransaction:
    """A single payment transaction with known fraud outcome."""
    transaction_id: str
    amount: float
    product_cd: str           # W, H, C, R, S
    card_brand: str           # visa, mastercard, discover, amex
    card_type: str            # debit, credit
    device_type: str          # desktop, mobile
    email_domain: str         # gmail.com, yahoo.com, etc.
    risk_tier: str            # T1 through T5 (like loan grade A-G)
    is_fraud: bool            # ground truth outcome

    @property
    def risk_score(self) -> float:
        """
        Composite risk score [0.0, 1.0] derived from transaction features.
        Higher = riskier.
        """
        tier_risk = {
            "T1": 0.10, "T2": 0.25, "T3": 0.45, "T4": 0.65, "T5": 0.85,
        }
        base = tier_risk.get(self.risk_tier, 0.40)

        # Amount contribution (log-scaled, larger = riskier)
        amount_factor = min(math.log1p(self.amount) / math.log1p(30000), 1.0) * 0.12

        # Device contribution (mobile = higher risk)
        device_factor = 0.08 if self.device_type == "mobile" else 0.0

        # Product code contribution
        product_risk = {"W": 0.0, "C": 0.03, "H": 0.05, "R": 0.06, "S": 0.07}
        product_factor = product_risk.get(self.product_cd, 0.04)

        return min(1.0, base + amount_factor + device_factor + product_factor)

    def to_task(self) -> Task:
        """Convert to a Syntropiq Task for governance processing."""
        risk = self.risk_score
        # Impact scales with transaction amount (fraud losses are the amount)
        impact = min(1.0, self.amount / 10000.0)
        # Fraud detection is real-time — high urgency
        urgency = 0.85

        return Task(
            id=self.transaction_id,
            impact=round(impact, 3),
            urgency=urgency,
            risk=round(risk, 3),
            metadata={
                "amount": self.amount,
                "product_cd": self.product_cd,
                "card_brand": self.card_brand,
                "card_type": self.card_type,
                "device_type": self.device_type,
                "email_domain": self.email_domain,
                "risk_tier": self.risk_tier,
                "is_fraud": self.is_fraud,
            },
        )


# ── Fraud rate curves (modeled on IEEE-CIS segment analysis) ──

# Real IEEE-CIS fraud rates by risk segment:
#   Overall: ~3.5%, but heavily concentrated in high-risk segments.
#   High-amount + mobile + product H/S: 20-40%
#   Low-amount + desktop + product W: 1-2%
FRAUD_RATES = {
    "T1": 0.01, "T2": 0.03, "T3": 0.08,
    "T4": 0.18, "T5": 0.35,
}

TIER_DISTRIBUTION = {
    "T1": 0.35, "T2": 0.30, "T3": 0.18,
    "T4": 0.10, "T5": 0.07,
}

PRODUCT_CODES = ["W", "H", "C", "R", "S"]
PRODUCT_WEIGHTS = {
    "T1": [0.85, 0.03, 0.08, 0.02, 0.02],
    "T2": [0.70, 0.08, 0.14, 0.04, 0.04],
    "T3": [0.45, 0.15, 0.20, 0.10, 0.10],
    "T4": [0.25, 0.20, 0.20, 0.17, 0.18],
    "T5": [0.15, 0.25, 0.15, 0.22, 0.23],
}

CARD_BRANDS = ["visa", "mastercard", "discover", "amex"]
CARD_BRAND_WEIGHTS = [0.55, 0.30, 0.10, 0.05]

CARD_TYPES = ["debit", "credit"]
CARD_TYPE_WEIGHTS_BY_TIER = {
    "T1": [0.45, 0.55],
    "T2": [0.50, 0.50],
    "T3": [0.55, 0.45],
    "T4": [0.60, 0.40],
    "T5": [0.65, 0.35],
}

DEVICE_TYPES = ["desktop", "mobile"]
DEVICE_WEIGHTS_BY_TIER = {
    "T1": [0.80, 0.20],
    "T2": [0.65, 0.35],
    "T3": [0.50, 0.50],
    "T4": [0.35, 0.65],
    "T5": [0.25, 0.75],
}

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "icloud.com", "protonmail.com", "corporate.com",
]


def _pick_tier(rng: random.Random) -> str:
    """Weighted random tier selection."""
    r = rng.random()
    cumulative = 0.0
    for tier, prob in TIER_DISTRIBUTION.items():
        cumulative += prob
        if r <= cumulative:
            return tier
    return "T2"


def _generate_transaction(
    tx_id: str, rng: random.Random, tier: Optional[str] = None,
) -> FraudTransaction:
    """Generate a single realistic fraud transaction."""
    if tier is None:
        tier = _pick_tier(rng)

    # Amount ranges by tier (log-normal, different scales)
    amount_params = {
        "T1": (3.5, 0.8),   # median ~$33
        "T2": (4.2, 0.9),   # median ~$67
        "T3": (5.0, 1.0),   # median ~$148
        "T4": (5.8, 1.1),   # median ~$330
        "T5": (6.5, 1.2),   # median ~$665
    }
    mu, sigma = amount_params[tier]
    amount = round(min(31000, max(0.50, rng.lognormvariate(mu, sigma))), 2)

    product_cd = rng.choices(PRODUCT_CODES, weights=PRODUCT_WEIGHTS[tier])[0]
    card_brand = rng.choices(CARD_BRANDS, weights=CARD_BRAND_WEIGHTS)[0]
    card_type = rng.choices(CARD_TYPES, weights=CARD_TYPE_WEIGHTS_BY_TIER[tier])[0]
    device_type = rng.choices(DEVICE_TYPES, weights=DEVICE_WEIGHTS_BY_TIER[tier])[0]
    email_domain = rng.choice(EMAIL_DOMAINS)

    # Fraud outcome based on tier fraud rate
    is_fraud = rng.random() < FRAUD_RATES[tier]

    return FraudTransaction(
        transaction_id=tx_id,
        amount=amount,
        product_cd=product_cd,
        card_brand=card_brand,
        card_type=card_type,
        device_type=device_type,
        email_domain=email_domain,
        risk_tier=tier,
        is_fraud=is_fraud,
    )


def generate_fraud_batch(
    batch_size: int = 10,
    batch_id: int = 0,
    seed: Optional[int] = None,
    risk_profile: str = "mixed",
) -> List[FraudTransaction]:
    """
    Generate a batch of realistic fraud transactions.

    Args:
        batch_size: Number of transactions per batch
        batch_id: Batch identifier (used in transaction IDs)
        seed: Random seed for reproducibility
        risk_profile: "mixed" (normal), "high_risk" (T3-T5 heavy),
                      or "low_risk" (T1-T2 heavy)
    """
    rng = random.Random(seed if seed is not None else batch_id)

    if risk_profile == "high_risk":
        return [
            _generate_high_risk_transaction(f"TX_{batch_id:03d}_{i:03d}", rng)
            for i in range(batch_size)
        ]
    elif risk_profile == "low_risk":
        return [
            _generate_low_risk_transaction(f"TX_{batch_id:03d}_{i:03d}", rng)
            for i in range(batch_size)
        ]

    return [
        _generate_transaction(f"TX_{batch_id:03d}_{i:03d}", rng)
        for i in range(batch_size)
    ]


def _generate_high_risk_transaction(
    tx_id: str, rng: random.Random,
) -> FraudTransaction:
    """
    Generate a high-risk transaction (Tier T3-T5).
    These are the transactions a drifting agent will pass that shouldn't be passed.
    """
    tier = rng.choices(
        ["T3", "T4", "T5"],
        weights=[0.35, 0.40, 0.25],
    )[0]
    return _generate_transaction(tx_id, rng, tier=tier)


def _generate_low_risk_transaction(
    tx_id: str, rng: random.Random,
) -> FraudTransaction:
    """Generate a low-risk transaction (Tier T1-T2) for redemption phases."""
    tier = rng.choices(["T1", "T2"], weights=[0.55, 0.45])[0]
    return _generate_transaction(tx_id, rng, tier=tier)


def load_ieee_cis_csv(
    csv_path: str,
    max_rows: int = 5000,
) -> List[FraudTransaction]:
    """
    Load curated IEEE-CIS data from CSV.

    Expected columns: transaction_id, amount, product_cd, card_brand,
    card_type, device_type, email_domain, risk_tier, is_fraud

    Args:
        csv_path: Path to curated IEEE-CIS CSV file
        max_rows: Maximum rows to load
    """
    transactions = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            try:
                is_fraud_raw = row.get("is_fraud", "0").strip()
                is_fraud = is_fraud_raw in ("1", "True", "true", "yes")

                tx = FraudTransaction(
                    transaction_id=f"CIS_{i:06d}",
                    amount=float(row.get("amount", 0)),
                    product_cd=row.get("product_cd", "W").strip(),
                    card_brand=row.get("card_brand", "visa").strip(),
                    card_type=row.get("card_type", "debit").strip(),
                    device_type=row.get("device_type", "desktop").strip(),
                    email_domain=row.get("email_domain", "gmail.com").strip(),
                    risk_tier=row.get("risk_tier", "T2").strip(),
                    is_fraud=is_fraud,
                )
                transactions.append(tx)
            except (ValueError, KeyError):
                continue

    return transactions


# ── Real Data Pool ───────────────────────────────────────────

# Tier groups for phase-based sampling
_SAFE_TIERS = {"T1", "T2"}
_RISKY_TIERS = {"T3", "T4", "T5"}


class RealDataPool:
    """
    Pool of real IEEE-CIS transactions that serves phase-appropriate batches.

    Loads the curated sample CSV (from prepare_data.py) and indexes
    transactions by risk tier. Each call to sample_batch() draws
    transactions matching the requested risk profile, without replacement.
    """

    def __init__(self, csv_path: str = None, seed: int = 42):
        self.csv_path = csv_path or str(SAMPLE_CSV_PATH)
        self.rng = random.Random(seed)

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"No curated data at: {self.csv_path}\n"
                f"Run: python -m syntropiq.demo.fraud.prepare_data "
                f"<train_transaction.csv> <train_identity.csv>"
            )

        all_txns = load_ieee_cis_csv(self.csv_path, max_rows=10000)
        if not all_txns:
            raise ValueError(f"No valid transactions in: {self.csv_path}")

        # Index by risk tier
        self._safe = [t for t in all_txns if t.risk_tier in _SAFE_TIERS]
        self._risky = [t for t in all_txns if t.risk_tier in _RISKY_TIERS]
        self._mixed = list(all_txns)

        self.rng.shuffle(self._safe)
        self.rng.shuffle(self._risky)
        self.rng.shuffle(self._mixed)

        self._safe_idx = 0
        self._risky_idx = 0
        self._mixed_idx = 0

        self.total_txns = len(all_txns)
        self.total_fraud = sum(1 for t in all_txns if t.is_fraud)
        self.fraud_rate = self.total_fraud / self.total_txns

    def sample_batch(
        self,
        batch_size: int,
        batch_id: int,
        risk_profile: str = "mixed",
    ) -> List[FraudTransaction]:
        """Draw a batch of real transactions matching the risk profile."""
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

            tx = pool[cursor]
            cursor += 1

            batch.append(FraudTransaction(
                transaction_id=f"CIS_{batch_id:03d}_{i:03d}",
                amount=tx.amount,
                product_cd=tx.product_cd,
                card_brand=tx.card_brand,
                card_type=tx.card_type,
                device_type=tx.device_type,
                email_domain=tx.email_domain,
                risk_tier=tx.risk_tier,
                is_fraud=tx.is_fraud,
            ))

        setattr(self, cursor_attr, cursor)
        return batch

    @property
    def description(self) -> str:
        return (
            f"IEEE-CIS ({self.total_txns:,} real transactions, "
            f"{self.fraud_rate:.1%} fraud rate)"
        )

    @staticmethod
    def is_available(csv_path: str = None) -> bool:
        path = csv_path or str(SAMPLE_CSV_PATH)
        return os.path.exists(path)
