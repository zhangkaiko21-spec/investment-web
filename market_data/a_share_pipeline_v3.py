#!/usr/bin/env python3
"""Safety wrapper for 周月箱体复利战法2.1 pipeline.

This wrapper keeps the lightweight v2 data path, but adds two hard guarantees:
1. No decision or forced-close action can be generated outside the permitted
   Beijing-time execution window.
2. JSON and ledger invariants are validated before a run is considered healthy.
"""

from __future__ import annotations

import json
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Any

import a_share_pipeline as core
import a_share_pipeline_v2 as v2

TAIL_START = dtime(14, 35)
TAIL_DECISION_END = dtime(14, 58)
FORCED_CLOSE_END = dtime(15, 0)

LOCKED_HISTORY = {
    ("000651", "SELL", 100, 39.06),
    ("600887", "SELL", 100, 25.30),
    ("000651", "SELL", 100, 39.20),
}


def safe_resolve_effective_mode(
    requested_mode: str,
    now: datetime,
    account: dict[str, Any],
    cfg: dict[str, Any],
) -> tuple[str, str]:
    """Reject late scheduler runs instead of creating retroactive trades."""
    if requested_mode == "bootstrap":
        return "bootstrap", "history maintenance"
    if requested_mode not in {"decision", "close"}:
        return "intraday", "intraday observation"
    if not core.is_trading_day(now.date(), cfg):
        return "intraday", "request arrived on a non-trading day"

    clock = now.time()
    forced_close = core.parse_day(account["cycle"]["forced_close"])

    if now.date() >= forced_close:
        if TAIL_START <= clock <= FORCED_CLOSE_END:
            return "close", "inside forced-settlement window 14:35-15:00"
        return "intraday", "forced-settlement request outside 14:35-15:00"

    if requested_mode == "decision" and TAIL_START <= clock <= TAIL_DECISION_END:
        return "decision", "inside Beijing tail decision window 14:35-14:58"

    return "intraday", "decision request outside 14:35-14:58"


def load_required() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    health = core.load_json(core.DATA_DIR / "health.json", {})
    decision = core.load_json(core.DATA_DIR / "decision.json", {})
    account = core.load_json(core.DATA_DIR / "account_state.json", {})
    return health, decision, account


def mark_invariant_failure(health: dict[str, Any], errors: list[str]) -> None:
    health.update(
        {
            "ok": False,
            "pipeline_ok": False,
            "trade_allowed": False,
            "status": "ledger_invariant_failed",
            "invariant_errors": errors,
            "validated_at": core.now_cn().isoformat(timespec="seconds"),
        }
    )
    core.atomic_write_json(core.DATA_DIR / "health.json", health)


def validate_outputs() -> int:
    errors: list[str] = []
    required = [
        "health.json",
        "market_summary.json",
        "candidates.json",
        "decision.json",
        "account_state.json",
    ]
    missing = [name for name in required if not (core.DATA_DIR / name).exists()]
    if missing:
        errors.append(f"missing files: {missing}")

    health, decision, account = load_required()
    today = core.now_cn().date().isoformat()

    for label, payload in (("health", health), ("decision", decision), ("account", account)):
        if not isinstance(payload, dict) or not payload:
            errors.append(f"{label} is missing or invalid")

    if health.get("market_date") != today:
        errors.append("health.market_date does not match current Beijing date")
    if decision.get("market_date") != today:
        errors.append("decision.market_date does not match current Beijing date")
    if account.get("market_date") != today:
        errors.append("account.market_date does not match current Beijing date")
    if not account.get("generated_at") or not account.get("updated_at"):
        errors.append("account timestamps are incomplete")

    summary = decision.get("account_summary") or {}
    for key in ("cash", "market_value", "equity", "holdings", "cycle"):
        if summary.get(key) != account.get(key):
            errors.append(f"decision/account mismatch: {key}")

    trades = account.get("trades") or []
    trade_ids = [item.get("id") for item in trades if item.get("id")]
    if len(trade_ids) != len(set(trade_ids)):
        errors.append("duplicate trade id in unique ledger")

    locked = {
        (
            str(item.get("code")),
            str(item.get("action")),
            int(item.get("shares") or 0),
            round(float(item.get("price") or 0), 2),
        )
        for item in (account.get("locked_trades") or [])
    }
    if not LOCKED_HISTORY.issubset(locked):
        errors.append("locked historical trades are missing or altered")

    actions = decision.get("actions") or []
    if actions and not health.get("trade_allowed"):
        errors.append("actions exist while health.trade_allowed is false")

    action_ids = [item.get("id") for item in actions if item.get("id")]
    if any(action_id not in set(trade_ids) for action_id in action_ids):
        errors.append("decision action is not recorded in the unique ledger")

    if errors:
        mark_invariant_failure(health, errors)
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False))
        return 4

    health["invariants_ok"] = True
    health["validated_at"] = core.now_cn().isoformat(timespec="seconds")
    core.atomic_write_json(core.DATA_DIR / "health.json", health)
    print(json.dumps({"ok": True, "invariants_ok": True}, ensure_ascii=False))
    return 0


def main() -> int:
    v2.resolve_effective_mode = safe_resolve_effective_mode
    exit_code = v2.main()
    if exit_code != 0:
        return exit_code
    return validate_outputs()


if __name__ == "__main__":
    raise SystemExit(main())
