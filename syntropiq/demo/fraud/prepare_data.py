"""
IEEE-CIS Fraud Detection Data Preparation

Curates the raw IEEE-CIS Kaggle dataset into a compact sample optimized for
the Syntropiq governance demo.  The output file contains ~2000 transactions
with known outcomes (isFraud 0/1), stratified by computed risk tier to
ensure all risk levels are represented.

Usage:
    python -m syntropiq.demo.fraud.prepare_data train_transaction.csv train_identity.csv

    The raw CSVs can be downloaded from:
      https://www.kaggle.com/competitions/ieee-fraud-detection/data

    Required files: train_transaction.csv, train_identity.csv

Output:
    syntropiq/demo/fraud/data/ieee_cis_sample.csv
    (~2000 rows, <500KB, suitable for version control)
"""

import argparse
import csv
import math
import os
import random
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_PATH = DATA_DIR / "ieee_cis_sample.csv"

# Target rows per risk tier for a balanced demo sample
TARGET_PER_TIER = {
    "T1": 500, "T2": 500, "T3": 400,
    "T4": 350, "T5": 250,
}
TOTAL_TARGET = sum(TARGET_PER_TIER.values())  # 2000

# Free email domains (higher fraud signal)
FREE_EMAILS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "aol.com", "icloud.com", "protonmail.com", "mail.com",
    "ymail.com", "live.com", "msn.com",
}

# Output columns
OUTPUT_FIELDS = [
    "transaction_id", "amount", "product_cd", "card_brand",
    "card_type", "device_type", "email_domain", "risk_tier", "is_fraud",
]


def compute_risk_tier(row: dict) -> str:
    """
    Compute a risk tier (T1-T5) from raw IEEE-CIS features.

    Combines amount, product code, device type, and card type into a
    composite risk score, then buckets into tiers.
    """
    score = 0.0

    # Amount contribution (log-scaled)
    try:
        amount = float(row.get("TransactionAmt", 0))
    except (ValueError, TypeError):
        amount = 0.0
    if amount > 0:
        score += min(math.log1p(amount) / math.log1p(30000), 1.0) * 0.30

    # Product code risk
    product_cd = row.get("ProductCD", "W").strip()
    product_risk = {"W": 0.0, "C": 0.15, "H": 0.25, "R": 0.30, "S": 0.35}
    score += product_risk.get(product_cd, 0.20) * 0.25

    # Device type risk (mobile = higher)
    device_type = row.get("DeviceType", "").strip().lower()
    if device_type == "mobile":
        score += 0.30 * 0.20
    # Desktop or unknown: 0

    # Card type risk
    card_type = row.get("card6", "").strip().lower()
    if card_type == "debit":
        score += 0.10 * 0.15

    # Email domain risk (free email = slightly higher)
    email = row.get("P_emaildomain", "").strip().lower()
    if email in FREE_EMAILS:
        score += 0.10 * 0.10

    # Bucket into tiers
    if score < 0.12:
        return "T1"
    elif score < 0.22:
        return "T2"
    elif score < 0.35:
        return "T3"
    elif score < 0.50:
        return "T4"
    else:
        return "T5"


def curate_csv(
    transaction_path: str,
    identity_path: str,
    output_path: str = None,
    seed: int = 42,
) -> dict:
    """
    Read raw IEEE-CIS CSVs, join identity features, compute risk tiers,
    stratified sample, and write a compact output.
    """
    output_path = output_path or str(SAMPLE_PATH)
    rng = random.Random(seed)

    # Step 1: Load identity data (indexed by TransactionID)
    print(f"  Loading identity: {identity_path}")
    identity = {}
    with open(identity_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = row.get("TransactionID", "").strip()
            if tid:
                identity[tid] = row

    print(f"  Identity records: {len(identity):,}")

    # Step 2: Process transactions with joined identity
    print(f"  Loading transactions: {transaction_path}")
    by_tier = {t: [] for t in ["T1", "T2", "T3", "T4", "T5"]}
    total_read = 0
    skipped = Counter()

    with open(transaction_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_read += 1
            if total_read % 100000 == 0:
                print(f"    ... processed {total_read:,} rows")

            # Validate essential fields
            tid = row.get("TransactionID", "").strip()
            if not tid:
                skipped["no_id"] += 1
                continue

            try:
                amount = float(row.get("TransactionAmt", 0))
                is_fraud = int(row.get("isFraud", -1))
            except (ValueError, TypeError):
                skipped["parse_error"] += 1
                continue

            if is_fraud not in (0, 1):
                skipped["bad_label"] += 1
                continue
            if amount <= 0:
                skipped["bad_amount"] += 1
                continue

            # Join identity (left join — not all transactions have identity)
            id_row = identity.get(tid, {})

            # Merge identity fields into row for risk scoring
            row["DeviceType"] = id_row.get("DeviceType", "")
            row["DeviceInfo"] = id_row.get("DeviceInfo", "")

            tier = compute_risk_tier(row)

            # Normalize fields for output
            card_brand = row.get("card4", "unknown").strip().lower()
            card_type = row.get("card6", "unknown").strip().lower()
            device_type = id_row.get("DeviceType", "desktop").strip().lower()
            if device_type not in ("desktop", "mobile"):
                device_type = "desktop"
            email = row.get("P_emaildomain", "unknown").strip().lower()

            by_tier[tier].append({
                "transaction_id": tid,
                "amount": f"{amount:.2f}",
                "product_cd": row.get("ProductCD", "W").strip(),
                "card_brand": card_brand,
                "card_type": card_type,
                "device_type": device_type,
                "email_domain": email,
                "risk_tier": tier,
                "is_fraud": str(is_fraud),
            })

    print(f"  Total rows read: {total_read:,}")
    for tier in ["T1", "T2", "T3", "T4", "T5"]:
        n = len(by_tier[tier])
        frauds = sum(1 for r in by_tier[tier] if r["is_fraud"] == "1")
        rate = frauds / n if n else 0
        print(f"    Tier {tier}: {n:,} transactions ({rate:.1%} fraud)")

    if skipped:
        print(f"  Skipped: {dict(skipped)}")

    # Step 3: Stratified sampling
    sample = []
    for tier, target in TARGET_PER_TIER.items():
        pool = by_tier[tier]
        if len(pool) <= target:
            sample.extend(pool)
        else:
            sample.extend(rng.sample(pool, target))

    rng.shuffle(sample)

    # Step 4: Write compact output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in sample:
            writer.writerow(row)

    sample_frauds = sum(1 for r in sample if r["is_fraud"] == "1")
    sample_rate = sample_frauds / len(sample) if sample else 0

    stats = {
        "total_read": total_read,
        "identity_records": len(identity),
        "sample_size": len(sample),
        "sample_fraud_rate": round(sample_rate, 3),
        "output_path": output_path,
        "by_tier": {
            t: len([r for r in sample if r["risk_tier"] == t])
            for t in ["T1", "T2", "T3", "T4", "T5"]
        },
    }

    file_size = os.path.getsize(output_path)
    print(f"\n  Sample written: {output_path}")
    print(f"  Sample size: {len(sample):,} transactions ({file_size / 1024:.0f} KB)")
    print(f"  Fraud rate: {sample_rate:.1%}")
    print(f"  Tier distribution: {stats['by_tier']}")
    print(f"\n  Ready for: python -m syntropiq.demo.fraud.run --real-data")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Curate IEEE-CIS data for the Syntropiq fraud governance demo"
    )
    parser.add_argument(
        "transaction_csv",
        help="Path to train_transaction.csv",
    )
    parser.add_argument(
        "identity_csv",
        help="Path to train_identity.csv",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(SAMPLE_PATH),
        help=f"Output path (default: {SAMPLE_PATH})",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )

    args = parser.parse_args()

    for path, label in [
        (args.transaction_csv, "train_transaction.csv"),
        (args.identity_csv, "train_identity.csv"),
    ]:
        if not os.path.exists(path):
            print(f"  Error: File not found: {path}", file=sys.stderr)
            print(f"\n  Download IEEE-CIS data from:", file=sys.stderr)
            print(f"    https://www.kaggle.com/competitions/"
                  f"ieee-fraud-detection/data", file=sys.stderr)
            sys.exit(1)

    print("=" * 60)
    print("  SYNTROPIQ — IEEE-CIS Fraud Data Preparation")
    print("=" * 60)

    curate_csv(args.transaction_csv, args.identity_csv, args.output, args.seed)


if __name__ == "__main__":
    main()
