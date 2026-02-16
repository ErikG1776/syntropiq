"""
Lending Club Data Preparation

Curates a real Lending Club CSV into a compact sample optimized for the
Syntropiq governance demo. The output file contains ~2000 loans with
known outcomes (Fully Paid or Charged Off), stratified by grade to
ensure all risk tiers are represented.

Usage:
    python -m syntropiq.demo.lending.prepare_data path/to/lending_club.csv

    The raw CSV can be downloaded from:
      - Kaggle: https://www.kaggle.com/datasets/wordsforthewise/lending-club
      - LendingClub archive (historical data, pre-2020)

    Accepted columns: loan_amnt, term, int_rate, grade, sub_grade,
    annual_inc, dti, purpose, home_ownership, loan_status

Output:
    syntropiq/demo/lending/data/lending_club_sample.csv
    (~2000 rows, <500KB, suitable for version control)
"""

import argparse
import csv
import os
import random
import sys
from collections import Counter
from pathlib import Path

# Where the curated sample lives
DATA_DIR = Path(__file__).parent / "data"
SAMPLE_PATH = DATA_DIR / "lending_club_sample.csv"

# Target rows per grade for a balanced demo sample
# Over-represent risky grades slightly so the stress phase has enough data
TARGET_PER_GRADE = {
    "A": 300, "B": 400, "C": 350, "D": 300,
    "E": 250, "F": 200, "G": 150,
}
TOTAL_TARGET = sum(TARGET_PER_GRADE.values())  # 1950

# Fields we keep (everything the demo needs, nothing else)
KEEP_FIELDS = [
    "loan_amnt", "term", "int_rate", "grade", "sub_grade",
    "annual_inc", "dti", "purpose", "home_ownership", "loan_status",
]

VALID_STATUSES = {"Fully Paid", "Charged Off", "Default"}


def curate_csv(input_path: str, output_path: str = None, seed: int = 42) -> dict:
    """
    Read a raw Lending Club CSV, filter to resolved loans, stratify
    by grade, and write a compact sample.

    Returns stats about the curation.
    """
    output_path = output_path or str(SAMPLE_PATH)
    rng = random.Random(seed)

    # First pass: collect all valid loans by grade
    by_grade = {g: [] for g in "ABCDEFG"}
    skipped = Counter()
    total_read = 0

    print(f"  Reading: {input_path}")
    print(f"  This may take a moment for large files...")

    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for row in reader:
            total_read += 1
            if total_read % 100000 == 0:
                print(f"    ... processed {total_read:,} rows")

            # Filter to resolved loans only
            status = row.get("loan_status", "").strip()
            if status not in VALID_STATUSES:
                skipped[f"status:{status[:30]}"] += 1
                continue

            grade = row.get("grade", "").strip()
            if grade not in by_grade:
                skipped["bad_grade"] += 1
                continue

            # Validate key numeric fields
            try:
                amt = float(row.get("loan_amnt", 0))
                inc = float(row.get("annual_inc", 0))
                rate_str = row.get("int_rate", "0").replace("%", "").strip()
                rate = float(rate_str)
                dti_val = row.get("dti", "")
                dti = float(dti_val) if dti_val.strip() else 0.0
            except (ValueError, TypeError):
                skipped["parse_error"] += 1
                continue

            if amt <= 0 or inc <= 0 or rate <= 0:
                skipped["invalid_values"] += 1
                continue

            by_grade[grade].append(row)

    print(f"  Total rows read: {total_read:,}")
    for grade in "ABCDEFG":
        n = len(by_grade[grade])
        defaults = sum(
            1 for r in by_grade[grade]
            if r.get("loan_status", "").strip() in ("Charged Off", "Default")
        )
        rate = defaults / n if n else 0
        print(f"    Grade {grade}: {n:,} loans ({rate:.1%} default)")

    # Stratified sampling
    sample = []
    for grade, target in TARGET_PER_GRADE.items():
        pool = by_grade[grade]
        if len(pool) <= target:
            sample.extend(pool)
        else:
            sample.extend(rng.sample(pool, target))

    rng.shuffle(sample)

    # Write compact output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=KEEP_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in sample:
            # Normalize fields
            row["int_rate"] = row.get("int_rate", "0").replace("%", "").strip()
            term_raw = row.get("term", "36")
            row["term"] = term_raw.strip().split()[0] if term_raw else "36"
            writer.writerow(row)

    # Compute stats for the sample
    sample_defaults = sum(
        1 for r in sample
        if r.get("loan_status", "").strip() in ("Charged Off", "Default")
    )
    sample_rate = sample_defaults / len(sample) if sample else 0

    stats = {
        "total_read": total_read,
        "sample_size": len(sample),
        "sample_default_rate": round(sample_rate, 3),
        "output_path": output_path,
        "by_grade": {
            g: len([r for r in sample if r.get("grade") == g])
            for g in "ABCDEFG"
        },
    }

    file_size = os.path.getsize(output_path)
    print(f"\n  Sample written: {output_path}")
    print(f"  Sample size: {len(sample):,} loans ({file_size / 1024:.0f} KB)")
    print(f"  Default rate: {sample_rate:.1%}")
    print(f"  Grade distribution: {stats['by_grade']}")
    print(f"\n  Ready for: python -m syntropiq.demo.lending.run --real-data")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Curate Lending Club data for the Syntropiq governance demo"
    )
    parser.add_argument(
        "input_csv",
        help="Path to raw Lending Club CSV (from Kaggle or LC archive)",
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

    if not os.path.exists(args.input_csv):
        print(f"  Error: File not found: {args.input_csv}", file=sys.stderr)
        print(f"\n  Download Lending Club data from:", file=sys.stderr)
        print(f"    https://www.kaggle.com/datasets/wordsforthewise/lending-club",
              file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("  SYNTROPIQ — Lending Club Data Preparation")
    print("=" * 60)

    curate_csv(args.input_csv, args.output, args.seed)


if __name__ == "__main__":
    main()
