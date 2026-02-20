"""
UCI Diabetes 130-US Hospitals Readmission Data Preparation

Curates the raw UCI dataset (diabetic_data.csv) into a compact sample
optimized for the Syntropiq governance demo.  The output file contains
~2500 encounters with known outcomes, stratified by computed risk tier
to ensure all risk levels are represented.

Usage:
    python -m syntropiq.demo.readmission.prepare_data diabetic_data.csv

    The raw CSV can be downloaded from:
      https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008
    Or from GitHub mirrors / Kaggle:
      https://www.kaggle.com/datasets/brandao/diabetes

    Required file: diabetic_data.csv (101,766 rows, ~19MB)

Output:
    syntropiq/demo/readmission/data/diabetes_readmission_sample.csv
    (~2500 rows, <200KB, suitable for version control)
"""

import argparse
import csv
import os
import random
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_PATH = DATA_DIR / "diabetes_readmission_sample.csv"

# Target rows per risk tier for a balanced demo sample
TARGET_PER_TIER = {
    "R1": 600, "R2": 600, "R3": 500,
    "R4": 450, "R5": 350,
}
TOTAL_TARGET = sum(TARGET_PER_TIER.values())  # 2500

# Output columns
OUTPUT_FIELDS = [
    "encounter_id", "age_group", "time_in_hospital", "num_medications",
    "num_diagnoses", "num_lab_procedures", "a1c_result", "insulin",
    "prior_inpatient", "prior_emergency", "discharge_disposition",
    "risk_tier", "readmitted_30d",
]

# Discharge disposition mapping (from raw codes to readable categories)
DISCHARGE_MAP = {
    "1": "Home",
    "6": "Home",
    "8": "Home",
    "3": "SNF",
    "4": "SNF",
    "5": "SNF",
    "2": "Other",       # Short-term hospital
    "22": "Home Health",
    "23": "Home Health",
    "24": "Home Health",
    "28": "Home Health",
}


def compute_risk_tier(row: dict) -> str:
    """
    Compute a risk tier (R1-R5) from raw UCI Diabetes features.

    Combines age, HbA1c, prior inpatient visits, number of medications,
    number of diagnoses, and time in hospital into a composite risk score.
    """
    score = 0.0

    # Age contribution (strongest predictor)
    age = row.get("age", "").strip()
    age_scores = {
        "[0-10)": 0.0, "[10-20)": 0.02, "[20-30)": 0.04, "[30-40)": 0.06,
        "[40-50)": 0.10, "[50-60)": 0.16, "[60-70)": 0.24,
        "[70-80)": 0.34, "[80-90)": 0.42, "[90-100)": 0.50,
    }
    score += age_scores.get(age, 0.16) * 0.30

    # HbA1c result (clinical risk signal)
    a1c = row.get("A1Cresult", "None").strip()
    a1c_scores = {"None": 0.05, "Norm": 0.0, ">7": 0.30, ">8": 0.50}
    score += a1c_scores.get(a1c, 0.05) * 0.20

    # Prior inpatient visits (recidivism — strongest readmission predictor)
    try:
        prior_inpat = int(row.get("number_inpatient", 0))
    except (ValueError, TypeError):
        prior_inpat = 0
    score += min(prior_inpat / 10.0, 1.0) * 0.20

    # Number of medications (complexity proxy)
    try:
        num_meds = int(row.get("num_medications", 15))
    except (ValueError, TypeError):
        num_meds = 15
    score += min(num_meds / 50.0, 1.0) * 0.10

    # Number of diagnoses (comorbidity burden)
    try:
        num_diag = int(row.get("number_diagnoses", 7))
    except (ValueError, TypeError):
        num_diag = 7
    score += min(num_diag / 16.0, 1.0) * 0.10

    # Time in hospital (acuity signal)
    try:
        time_hosp = int(row.get("time_in_hospital", 4))
    except (ValueError, TypeError):
        time_hosp = 4
    score += min(time_hosp / 14.0, 1.0) * 0.10

    # Bucket into tiers
    if score < 0.10:
        return "R1"
    elif score < 0.18:
        return "R2"
    elif score < 0.28:
        return "R3"
    elif score < 0.40:
        return "R4"
    else:
        return "R5"


def curate_csv(
    data_path: str,
    output_path: str = None,
    seed: int = 42,
) -> dict:
    """
    Read raw UCI Diabetes CSV, compute risk tiers, stratified sample,
    and write a compact output.
    """
    output_path = output_path or str(SAMPLE_PATH)
    rng = random.Random(seed)

    print(f"  Loading: {data_path}")
    by_tier = {t: [] for t in ["R1", "R2", "R3", "R4", "R5"]}
    total_read = 0
    skipped = Counter()

    with open(data_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_read += 1
            if total_read % 25000 == 0:
                print(f"    ... processed {total_read:,} rows")

            # Validate essential fields
            enc_id = row.get("encounter_id", "").strip()
            if not enc_id:
                skipped["no_id"] += 1
                continue

            # Readmission target: binarize to <30 days vs not
            readmitted_raw = row.get("readmitted", "NO").strip()
            readmitted_30d = 1 if readmitted_raw == "<30" else 0

            try:
                time_hosp = int(row.get("time_in_hospital", 0))
                num_meds = int(row.get("num_medications", 0))
                num_diag = int(row.get("number_diagnoses", 0))
                num_labs = int(row.get("num_lab_procedures", 0))
                prior_inpat = int(row.get("number_inpatient", 0))
                prior_er = int(row.get("number_emergency", 0))
            except (ValueError, TypeError):
                skipped["parse_error"] += 1
                continue

            if time_hosp <= 0:
                skipped["bad_time"] += 1
                continue

            tier = compute_risk_tier(row)

            # Normalize discharge disposition
            disp_id = row.get("discharge_disposition_id", "1").strip()
            discharge = DISCHARGE_MAP.get(disp_id, "Other")

            # HbA1c result
            a1c = row.get("A1Cresult", "None").strip()

            # Insulin
            insulin = row.get("insulin", "No").strip()

            # Age group
            age_group = row.get("age", "[50-60)").strip()

            by_tier[tier].append({
                "encounter_id": enc_id,
                "age_group": age_group,
                "time_in_hospital": str(time_hosp),
                "num_medications": str(num_meds),
                "num_diagnoses": str(num_diag),
                "num_lab_procedures": str(num_labs),
                "a1c_result": a1c,
                "insulin": insulin,
                "prior_inpatient": str(prior_inpat),
                "prior_emergency": str(prior_er),
                "discharge_disposition": discharge,
                "risk_tier": tier,
                "readmitted_30d": str(readmitted_30d),
            })

    print(f"  Total rows read: {total_read:,}")
    for tier in ["R1", "R2", "R3", "R4", "R5"]:
        n = len(by_tier[tier])
        readmits = sum(1 for r in by_tier[tier] if r["readmitted_30d"] == "1")
        rate = readmits / n if n else 0
        print(f"    Tier {tier}: {n:,} encounters ({rate:.1%} readmitted <30d)")

    if skipped:
        print(f"  Skipped: {dict(skipped)}")

    # Stratified sampling
    sample = []
    for tier, target in TARGET_PER_TIER.items():
        pool = by_tier[tier]
        if len(pool) <= target:
            sample.extend(pool)
        else:
            sample.extend(rng.sample(pool, target))

    rng.shuffle(sample)

    # Write compact output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in sample:
            writer.writerow(row)

    sample_readmits = sum(1 for r in sample if r["readmitted_30d"] == "1")
    sample_rate = sample_readmits / len(sample) if sample else 0

    stats = {
        "total_read": total_read,
        "sample_size": len(sample),
        "sample_readmission_rate": round(sample_rate, 3),
        "output_path": output_path,
        "by_tier": {
            t: len([r for r in sample if r["risk_tier"] == t])
            for t in ["R1", "R2", "R3", "R4", "R5"]
        },
    }

    file_size = os.path.getsize(output_path)
    print(f"\n  Sample written: {output_path}")
    print(f"  Sample size: {len(sample):,} encounters ({file_size / 1024:.0f} KB)")
    print(f"  30-day readmission rate: {sample_rate:.1%}")
    print(f"  Tier distribution: {stats['by_tier']}")
    print(f"\n  Ready for: python -m syntropiq.demo.readmission.run --real-data")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Curate UCI Diabetes data for the Syntropiq readmission governance demo"
    )
    parser.add_argument(
        "data_csv",
        help="Path to diabetic_data.csv",
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

    if not os.path.exists(args.data_csv):
        print(f"  Error: File not found: {args.data_csv}", file=sys.stderr)
        print(f"\n  Download the dataset from:", file=sys.stderr)
        print(f"    https://archive.ics.uci.edu/dataset/296", file=sys.stderr)
        print(f"    https://www.kaggle.com/datasets/brandao/diabetes", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("  SYNTROPIQ — UCI Diabetes Readmission Data Preparation")
    print("=" * 60)

    curate_csv(args.data_csv, args.output, args.seed)


if __name__ == "__main__":
    main()
