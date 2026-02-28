from __future__ import annotations

import json
import os

from syntropiq.optimize.schema import LambdaVector

_APPLIED_LAMBDA: dict[str, LambdaVector] = {}


def get_optimize_mode() -> str:
    mode = (os.getenv("OPTIMIZE_MODE") or "off").strip().lower()
    if mode in {"off", "score", "integrate"}:
        return mode
    return "off"


def get_lambda_adapt_mode() -> str:
    mode = (os.getenv("OPTIMIZE_LAMBDA_ADAPT_MODE") or "off").strip().lower()
    if mode in {"off", "log", "apply"}:
        return mode
    return "off"


def get_bayes_mode() -> str:
    mode = (os.getenv("OPTIMIZE_BAYES_MODE") or "off").strip().lower()
    if mode in {"off", "log", "apply"}:
        return mode
    return "off"


def get_default_lambda_vector() -> LambdaVector:
    defaults_json = os.getenv("OPTIMIZE_LAMBDA_DEFAULTS")

    if defaults_json:
        try:
            data = json.loads(defaults_json)
            lam = LambdaVector(
                l_cost=float(data.get("l_cost", 0.25)),
                l_time=float(data.get("l_time", 0.25)),
                l_risk=float(data.get("l_risk", 0.25)),
                l_trust=float(data.get("l_trust", 0.25)),
            )
            return lam.enforce_bounds().normalize()
        except Exception:
            pass

    lam = LambdaVector(
        l_cost=float(os.getenv("OPT_L_COST", "0.25")),
        l_time=float(os.getenv("OPT_L_TIME", "0.25")),
        l_risk=float(os.getenv("OPT_L_RISK", "0.25")),
        l_trust=float(os.getenv("OPT_L_TRUST", "0.25")),
    )
    return lam.enforce_bounds().normalize()


def get_current_lambda(run_id: str | None = None) -> LambdaVector:
    if run_id and run_id in _APPLIED_LAMBDA:
        current = _APPLIED_LAMBDA[run_id]
        return LambdaVector(**current.as_dict()).enforce_bounds().normalize()
    if "GLOBAL" in _APPLIED_LAMBDA:
        current = _APPLIED_LAMBDA["GLOBAL"]
        return LambdaVector(**current.as_dict()).enforce_bounds().normalize()
    return get_default_lambda_vector()


def set_current_lambda(new_lambda: LambdaVector, run_id: str | None = None) -> LambdaVector:
    key = run_id or "GLOBAL"
    normalized = LambdaVector(**new_lambda.as_dict()).enforce_bounds().normalize()
    _APPLIED_LAMBDA[key] = normalized
    return LambdaVector(**normalized.as_dict())
