#!/usr/bin/env python3
"""
Fetch real historical market data for Syntropiq finance demo.

- Source: yfinance daily adjusted close
- Tickers: QQQ, SPY, TLT, AGG, XLF, GLD, USO, EEM, IWM, HYG
- Period: 2021-01-01 through 2022-12-31
- Weekly return: Friday close (or last trading day in week) pct change
- Benchmark return: 0.60 * SPY + 0.40 * AGG
- Regime: stress when SPY 6-week rolling return < 0 OR 6-week vol > 75th percentile

Output schema is compatible with existing simulation pipeline.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Dict, List, Optional


DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(DATA_DIR, "market_data.json")

TICKERS = ["QQQ", "SPY", "TLT", "AGG", "XLF", "GLD", "USO", "EEM", "IWM", "HYG"]
BENCHMARK_WEIGHTS = {"SPY": 0.60, "AGG": 0.40}

START_MONDAY = date(2021, 1, 4)
END_FRIDAY = date(2022, 12, 30)
EXPECTED_WEEKS = 104


def _import_deps():
    try:
        import pandas as pd  # type: ignore
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        raise SystemExit("Missing dependency: pip install yfinance") from exc
    return pd, yf


def _extract_close_series(raw_df, ticker: str):
    import pandas as pd  # type: ignore

    if raw_df is None or raw_df.empty:
        return pd.Series(dtype="float64")

    if isinstance(raw_df.columns, pd.MultiIndex):
        if (ticker, "Close") in raw_df.columns:
            s = raw_df[(ticker, "Close")]
        elif ("Close", ticker) in raw_df.columns:
            s = raw_df[("Close", ticker)]
        elif ticker in raw_df.columns.get_level_values(0):
            sub = raw_df[ticker]
            s = sub["Close"] if "Close" in sub.columns else sub.iloc[:, 0]
        else:
            return pd.Series(dtype="float64")
    else:
        if ticker in raw_df.columns:
            s = raw_df[ticker]
        elif "Close" in raw_df.columns:
            s = raw_df["Close"]
        else:
            return pd.Series(dtype="float64")

    s = s.dropna().astype(float)
    s.index = pd.to_datetime(s.index)
    return s


def _download_daily_closes(tickers: List[str]):
    pd, yf = _import_deps()

    # include buffer before period so first weekly return can be computed
    raw = yf.download(
        tickers=tickers,
        start="2020-12-01",
        end="2023-01-10",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=False,
    )

    close_map = {ticker: _extract_close_series(raw, ticker) for ticker in tickers}

    # retry per-ticker fallback
    for ticker in tickers:
        if close_map[ticker].empty:
            retry = yf.download(
                tickers=ticker,
                start="2020-12-01",
                end="2023-01-10",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            close_map[ticker] = _extract_close_series(retry, ticker)

    return pd, close_map


def _week_fridays() -> List[date]:
    fridays: List[date] = []
    d = START_MONDAY + timedelta(days=4)
    while d <= END_FRIDAY:
        fridays.append(d)
        d += timedelta(days=7)
    return fridays


def _weekly_close_for_friday(series, friday: date) -> Optional[float]:
    """Last available close in the Mon-Fri window ending at `friday`."""
    week_start = friday - timedelta(days=4)
    mask = (series.index.date >= week_start) & (series.index.date <= friday)
    window = series.loc[mask]
    if window.empty:
        return None

    value = window.iloc[-1]

    # Handle scalar, 1-element Series, or 1-element array
    if hasattr(value, "item"):
        try:
            return float(value.item())
        except Exception:
            pass

    if hasattr(value, "values"):
        return float(value.values[0])

    return float(value)


def _previous_close_before(series, friday: date) -> Optional[float]:
    prev = series.loc[series.index.date < (friday - timedelta(days=4))]
    if prev.empty:
        return None
    v = prev.iloc[-1]
    if hasattr(v, "item"):
        try:
            return float(v.item())
        except Exception:
            pass
    if hasattr(v, "values"):
        return float(v.values[0])
    return float(v)


def _calc_regimes(spy_returns: List[float]) -> List[str]:
    regimes: List[str] = []
    rolling_means: List[float] = []
    rolling_vols: List[float] = []

    for i in range(len(spy_returns)):
        w = spy_returns[max(0, i - 5): i + 1]
        mean = sum(w) / len(w)
        rolling_means.append(mean)

        if len(w) > 1:
            w_mean = sum(w) / len(w)
            var = sum((x - w_mean) ** 2 for x in w) / len(w)
            vol = var ** 0.5
        else:
            vol = 0.0
        rolling_vols.append(vol)

    sorted_vols = sorted(rolling_vols)
    p75_idx = int(0.75 * (len(sorted_vols) - 1)) if sorted_vols else 0
    vol_p75 = sorted_vols[p75_idx] if sorted_vols else 0.0

    for mean, vol in zip(rolling_means, rolling_vols):
        regime = "stress" if (mean < 0.0 or vol > vol_p75) else "bull"
        regimes.append(regime)

    return regimes


def generate_market_data() -> Dict:
    pd, close_map = _download_daily_closes(TICKERS)

    for t in TICKERS:
        if close_map[t].empty:
            raise RuntimeError(f"No data fetched for ticker {t}")

    fridays = _week_fridays()

    temp_rows = []
    skipped = 0

    for friday in fridays:
        prices: Dict[str, float] = {}
        returns: Dict[str, float] = {}
        missing = False

        for t in TICKERS:
            s = close_map[t]
            close = _weekly_close_for_friday(s, friday)
            prev = _previous_close_before(s, friday)
            if close is None or prev is None or prev == 0:
                missing = True
                break

            ret = (close / prev) - 1.0
            prices[t] = round(close, 2)
            returns[t] = round(ret, 6)

        if missing:
            skipped += 1
            print(f"Skipping week ending {friday}: incomplete ticker coverage")
            continue

        benchmark_return = (
            BENCHMARK_WEIGHTS["SPY"] * returns["SPY"]
            + BENCHMARK_WEIGHTS["AGG"] * returns["AGG"]
        )

        temp_rows.append(
            {
                "friday": friday,
                "prices": prices,
                "returns": returns,
                "benchmark_return": round(benchmark_return, 6),
            }
        )

    if not temp_rows:
        raise RuntimeError("No weekly rows constructed from market data")

    spy_returns = [row["returns"]["SPY"] for row in temp_rows]
    regimes = _calc_regimes(spy_returns)

    weeks = []
    for idx, row in enumerate(temp_rows, start=1):
        monday = row["friday"] - timedelta(days=4)
        weeks.append(
            {
                "week": idx,
                "date": monday.isoformat(),
                "regime": regimes[idx - 1],
                "tickers": {
                    t: {
                        "price": row["prices"][t],
                        "weekly_return": row["returns"][t],
                    }
                    for t in TICKERS
                },
                "benchmark_return": row["benchmark_return"],
            }
        )

    first_stress = next((w["week"] for w in weeks if w["regime"] == "stress"), None)

    output = {
        "period": "2021-01-04 to 2022-12-30",
        "total_weeks": len(weeks),
        "regime_shift_week": first_stress,
        "tickers": TICKERS,
        "benchmark_composition": "60% SPY + 40% AGG",
        "weeks": weeks,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Market data written: {OUTPUT_PATH}")
    print(f"Weeks generated: {len(weeks)}")
    print(f"Date coverage: {weeks[0]['date']} -> {weeks[-1]['date']}")
    if skipped:
        print(f"Weeks skipped due to missing data: {skipped}")
    if len(weeks) != EXPECTED_WEEKS:
        print("Warning: weeks generated != 104 (data gaps/holidays handling)")

    return output


if __name__ == "__main__":
    generate_market_data()
