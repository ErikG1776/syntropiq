#!/usr/bin/env python3
"""
Fetch Market Data — Syntropiq Finance Demo

Generates weekly price/return data for the period January 4, 2021 through
December 30, 2022 (104 weeks). This window captures the full 2021 bull
regime followed by a rate-rise/stress regime.

Tickers:
    QQQ  — Nasdaq-100 (Growth Agent universe)
    TLT  — 20+ Year Treasury Bond (Risk Agent universe)
    SPY  — S&P 500 (Macro Agent universe)
    AGG  — US Aggregate Bond (benchmark blending)
    XLF  — Financials Sector (supplementary)

Benchmark: 60% SPY + 40% AGG

The data is calibrated so that:
- Bull phase: Growth-oriented assets (QQQ) clearly outperform; bonds underperform
- Stress phase: Growth crashes, bonds provide safety (flight-to-quality)
- This creates the governance narrative: Growth Agent suppressed in stress,
  Risk Agent elevated, governance protects capital

Output: market_data.json
"""

import json
import hashlib
import math
import os
from datetime import datetime, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(DATA_DIR, "market_data.json")

TICKERS = ["QQQ", "TLT", "SPY", "AGG", "XLF"]

START_PRICES = {
    "QQQ": 312.68,
    "TLT": 157.47,
    "SPY": 375.31,
    "AGG": 117.82,
    "XLF": 28.65,
}

# ── Weekly return parameters by regime ───────────────────────────
#
# Bull (2021): Strong growth, QQQ and SPY rally, bonds slightly negative
# Stress (2022): QQQ crashes hard, bonds provide flight-to-quality safety
#
# Key design: returns are calibrated so agents have clear regime performance:
#   Bull:   Growth Agent > Benchmark > Risk Agent
#   Stress: Risk Agent > Benchmark > Growth Agent
#
# This is the fundamental governance story — authority must shift.

REGIME_PARAMS = {
    "bull": {
        #           mean     vol   -- lower vol for cleaner regime signal
        "QQQ": {"mean":  0.0075, "vol": 0.008},  # Strong growth
        "SPY": {"mean":  0.0045, "vol": 0.006},  # Solid broad market
        "TLT": {"mean": -0.0015, "vol": 0.005},  # Bonds weak in bull
        "AGG": {"mean":  0.0002, "vol": 0.002},  # Bonds flat
        "XLF": {"mean":  0.0060, "vol": 0.009},  # Financials strong
    },
    "stress": {
        "QQQ": {"mean": -0.0070, "vol": 0.012},  # Tech crashes
        "SPY": {"mean": -0.0020, "vol": 0.010},  # Broad decline
        "TLT": {"mean":  0.0030, "vol": 0.006},  # Flight-to-quality
        "AGG": {"mean":  0.0012, "vol": 0.003},  # Bonds as safe haven
        "XLF": {"mean": -0.0025, "vol": 0.011},  # Financials hurt
    },
}


def _stable_hash(s: str) -> float:
    """Deterministic pseudo-random float in [0, 1) from a string seed."""
    h = int(hashlib.sha256(s.encode()).hexdigest(), 16)
    return (h % 1000000) / 1000000.0


def _box_muller(u1: float, u2: float):
    """Two uniform -> two standard normals."""
    r = math.sqrt(-2.0 * math.log(max(u1, 1e-10)))
    theta = 2.0 * math.pi * u2
    return r * math.cos(theta), r * math.sin(theta)


def _generate_returns(week: int, regime: str, seed: int = 2024):
    """Generate correlated weekly returns for all tickers."""
    params = REGIME_PARAMS[regime]

    # Generate normals per ticker
    normals = {}
    for ticker in TICKERS:
        u1 = _stable_hash(f"w{week}_t{ticker}_u1_s{seed}")
        u2 = _stable_hash(f"w{week}_t{ticker}_u2_s{seed}")
        z, _ = _box_muller(u1, u2)
        normals[ticker] = z

    # Correlate: equities move together, bonds inversely
    # QQQ independent
    raw = {}
    raw["QQQ"] = normals["QQQ"]

    # SPY correlated with QQQ (0.88 bull, 0.93 stress)
    rho_qs = 0.88 if regime == "bull" else 0.93
    raw["SPY"] = rho_qs * raw["QQQ"] + math.sqrt(1 - rho_qs**2) * normals["SPY"]

    # TLT negatively correlated with QQQ in bull, uncorrelated in stress
    rho_qt = -0.30 if regime == "bull" else 0.05
    raw["TLT"] = rho_qt * raw["QQQ"] + math.sqrt(1 - rho_qt**2) * normals["TLT"]

    # AGG correlated with TLT
    rho_ta = 0.80
    raw["AGG"] = rho_ta * raw["TLT"] + math.sqrt(1 - rho_ta**2) * normals["AGG"]

    # XLF correlated with SPY
    rho_xf = 0.75
    raw["XLF"] = rho_xf * raw["SPY"] + math.sqrt(1 - rho_xf**2) * normals["XLF"]

    # Scale to mean/vol
    returns = {}
    for ticker in TICKERS:
        p = params[ticker]
        returns[ticker] = p["mean"] + p["vol"] * raw[ticker]

    return returns


def generate_market_data(seed: int = 2024):
    """Generate 104 weeks of market data."""
    start_date = datetime(2021, 1, 4)
    weeks = []
    prices = dict(START_PRICES)

    for week_num in range(1, 105):
        regime = "bull" if week_num <= 52 else "stress"
        date = start_date + timedelta(weeks=week_num - 1)

        returns = _generate_returns(week_num, regime, seed)

        # Regime transition: extra volatility spike at week 52-54
        if 52 <= week_num <= 54:
            for ticker in TICKERS:
                if ticker in ("QQQ", "XLF"):
                    returns[ticker] -= 0.008  # Sharp equity sell-off
                elif ticker in ("TLT", "AGG"):
                    returns[ticker] += 0.004  # Flight to safety begins

        # Update prices
        week_data = {
            "week": week_num,
            "date": date.strftime("%Y-%m-%d"),
            "regime": regime,
            "tickers": {},
        }

        for ticker in TICKERS:
            ret = max(-0.10, min(0.08, returns[ticker]))
            new_price = prices[ticker] * (1.0 + ret)
            week_data["tickers"][ticker] = {
                "price": round(new_price, 2),
                "weekly_return": round(ret, 6),
            }
            prices[ticker] = new_price

        # Benchmark: 60% SPY + 40% AGG
        benchmark_return = (
            0.60 * week_data["tickers"]["SPY"]["weekly_return"]
            + 0.40 * week_data["tickers"]["AGG"]["weekly_return"]
        )
        week_data["benchmark_return"] = round(benchmark_return, 6)
        weeks.append(week_data)

    # Summary
    bull_weeks = [w for w in weeks if w["regime"] == "bull"]
    stress_weeks = [w for w in weeks if w["regime"] == "stress"]

    summary = {
        "period": "2021-01-04 to 2022-12-30",
        "total_weeks": len(weeks),
        "regime_shift_week": 53,
        "tickers": TICKERS,
        "benchmark_composition": "60% SPY + 40% AGG",
        "starting_portfolio": 10000000,
        "bull_phase": {
            "weeks": f"1-{len(bull_weeks)}",
            "ticker_returns": {
                ticker: round(
                    sum(w["tickers"][ticker]["weekly_return"] for w in bull_weeks), 4
                )
                for ticker in TICKERS
            },
        },
        "stress_phase": {
            "weeks": f"{len(bull_weeks)+1}-{len(weeks)}",
            "ticker_returns": {
                ticker: round(
                    sum(w["tickers"][ticker]["weekly_return"] for w in stress_weeks), 4
                )
                for ticker in TICKERS
            },
        },
    }

    output = {"summary": summary, "weeks": weeks}

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Market data generated: {OUTPUT_PATH}")
    print(f"  Period: {summary['period']}")
    print(f"  Weeks: {summary['total_weeks']}")
    print(f"  Regime shift: Week {summary['regime_shift_week']}")

    final_prices = {
        ticker: weeks[-1]["tickers"][ticker]["price"] for ticker in TICKERS
    }
    print(f"\n  Cumulative returns:")
    for ticker in TICKERS:
        total_ret = (final_prices[ticker] / START_PRICES[ticker] - 1) * 100
        print(f"    {ticker}: {total_ret:+.1f}%")

    # Show agent return characteristics
    for phase, phase_weeks in [("Bull", bull_weeks), ("Stress", stress_weeks)]:
        bm = sum(w["benchmark_return"] for w in phase_weeks)
        growth_r = sum(
            0.70 * w["tickers"]["QQQ"]["weekly_return"]
            + 0.20 * w["tickers"]["SPY"]["weekly_return"]
            + 0.10 * w["tickers"]["TLT"]["weekly_return"]
            for w in phase_weeks
        )
        risk_r = sum(
            0.15 * w["tickers"]["QQQ"]["weekly_return"]
            + 0.25 * w["tickers"]["SPY"]["weekly_return"]
            + 0.60 * w["tickers"]["TLT"]["weekly_return"]
            for w in phase_weeks
        )
        macro_r = sum(
            0.35 * w["tickers"]["QQQ"]["weekly_return"]
            + 0.45 * w["tickers"]["SPY"]["weekly_return"]
            + 0.20 * w["tickers"]["TLT"]["weekly_return"]
            for w in phase_weeks
        )
        print(f"\n  {phase} Phase — Agent returns vs benchmark ({bm:+.2%}):")
        print(f"    Growth: {growth_r:+.2%}  (delta: {growth_r - bm:+.2%})")
        print(f"    Risk:   {risk_r:+.2%}  (delta: {risk_r - bm:+.2%})")
        print(f"    Macro:  {macro_r:+.2%}  (delta: {macro_r - bm:+.2%})")

    return output


if __name__ == "__main__":
    generate_market_data()
