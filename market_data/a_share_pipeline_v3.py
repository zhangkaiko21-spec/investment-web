#!/usr/bin/env python3
"""Safety and snapshot wrapper for 周月箱体复利战法2.1.

Guarantees:
1. No decision or forced-close action can be generated outside the permitted
   Beijing-time execution window.
2. Intraday and tail runs prefer the reliable Sina full-market source, while
   final candidates still require Tencent cross-checks.
3. JSON and unique-ledger invariants are validated before a run is healthy.
4. Tail decisions are locked into tail_snapshot.json and are never overwritten
   by later intraday/bootstrap refreshes.
5. generated_at represents completed validation time; quote timestamps remain
   separate for strict trading-freshness checks.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, time as dtime
from typing import Any

import a_share_pipeline as core
import a_share_pipeline_v2 as v2

TAIL_START = dtime(14, 35)
TAIL_DECISION_END = dtime(14, 58)
FORCED_CLOSE_END = dtime(15, 0)
TAIL_SNAPSHOT_PATH = core.DATA_DIR / "tail_snapshot.json"

LOCKED_HISTORY = {
    ("000651", "SELL", 100, 39.06),
    ("600887", "SELL", 100, 25.30),
    ("000651", "SELL", 100, 39.20),
}

_ORIGINAL_BUILD_CANDIDATES = core.build_candidates


def requested_mode_from_argv() -> str:
    try:
        index = sys.argv.index("--mode")
        value = sys.argv[index + 1]
    except (ValueError, IndexError):
        return "intraday"
    return value if value in {"bootstrap", "intraday", "decision", "close"} else "intraday"


def stable_fetch_full_market() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Prefer Sina for time-critical runs because Eastmoney is frequently slow."""
    statuses: list[dict[str, Any]] = []
    rows, status = core.fetch_spot_sina()
    statuses.append(status.__dict__)
    if rows:
        return rows, statuses
    rows, status = core.fetch_spot_eastmoney()
    statuses.append(status.__dict__)
    return rows, statuses


def parse_secondary_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if len(text) == 14 and text.isdigit():
        try:
            return datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=core.TZ)
        except ValueError:
            return None
    return None


def build_candidates_with_fresh_crosscheck(
    spot_rows: list[dict[str, Any]],
    cache: dict[str, Any],
    cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], Any]:
    """Discard candidates whose Tencent cross-check is already stale."""
    candidates, status = _ORIGINAL_BUILD_CANDIDATES(spot_rows, cache, cfg)
    now = core.now_cn()
    maximum_age = int(cfg.get("maximum_trade_age_seconds", 900))
    fresh: list[dict[str, Any]] = []
    for candidate in candidates:
        secondary_at = parse_secondary_time(candidate.get("secondary_time"))
        if secondary_at is None:
            continue
        age = (now - secondary_at).total_seconds()
        if -60 <= age <= maximum_age:
            candidate["secondary_age_seconds"] = round(age, 1)
            fresh.append(candidate)
    return fresh, status


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
    completed_at = core.now_cn().isoformat(timespec="seconds")
    started_at = health.get("generated_at")
    if started_at:
        health["started_at"] = started_at
    health.update(
        {
            "generated_at": completed_at,
            "ok": False,
            "pipeline_ok": False,
            "trade_allowed": False,
            "status": "ledger_invariant_failed",
            "invariant_errors": errors,
            "validated_at": completed_at,
        }
    )
    core.atomic_write_json(core.DATA_DIR / "health.json", health)


def normalize_completion_timestamps(
    health: dict[str, Any],
    decision: dict[str, Any],
    account: dict[str, Any],
) -> str:
    """Make generated_at mean completion time, not process start time."""
    completed_at = core.now_cn().isoformat(timespec="seconds")

    health_started = health.get("generated_at")
    if health_started:
        health["started_at"] = health_started
    health["generated_at"] = completed_at
    health["validated_at"] = completed_at

    decision_started = decision.get("generated_at")
    if decision_started:
        decision["calculation_started_at"] = decision_started
    decision["generated_at"] = completed_at

    account_started = account.get("generated_at")
    if account_started:
        account["calculation_started_at"] = account_started
    account["generated_at"] = completed_at
    account["updated_at"] = completed_at

    for filename in ("candidates.json", "market_summary.json"):
        path = core.DATA_DIR / filename
        payload = core.load_json(path, {})
        if not isinstance(payload, dict) or not payload:
            continue
        started_at = payload.get("generated_at")
        if started_at:
            payload["calculation_started_at"] = started_at
        payload["generated_at"] = completed_at
        core.atomic_write_json(path, payload)

    core.atomic_write_json(core.DATA_DIR / "decision.json", decision)
    core.atomic_write_json(core.DATA_DIR / "account_state.json", account)
    core.atomic_write_json(core.DATA_DIR / "health.json", health)
    return completed_at


def seconds_between(later_iso: str, earlier_iso: str) -> float | None:
    try:
        later = datetime.fromisoformat(later_iso)
        earlier = datetime.fromisoformat(earlier_iso)
    except (TypeError, ValueError):
        return None
    return (later - earlier).total_seconds()


def write_tail_snapshot(
    health: dict[str, Any],
    decision: dict[str, Any],
    account: dict[str, Any],
    completed_at: str,
) -> None:
    """Lock a tail result; later intraday/bootstrap runs never overwrite it."""
    if health.get("requested_mode") not in {"decision", "close"}:
        return

    candidates_payload = core.load_json(core.DATA_DIR / "candidates.json", {})
    market_summary = core.load_json(core.DATA_DIR / "market_summary.json", {})
    actions = decision.get("actions") or []
    effective_mode = decision.get("effective_mode")
    base_valid = bool(
        health.get("pipeline_ok", health.get("ok"))
        and health.get("invariants_ok")
        and effective_mode in {"decision", "close"}
    )
    validation_errors: list[str] = []

    if not base_valid:
        validation_errors.append(
            f"effective_mode={effective_mode}, pipeline_ok={health.get('pipeline_ok')}, "
            f"invariants_ok={health.get('invariants_ok')}"
        )

    maximum_age = int(
        (health.get("freshness") or {}).get("maximum_trade_age_seconds") or 900
    )
    quote_received_at = (health.get("freshness") or {}).get("quote_received_at")
    quote_age = (
        seconds_between(completed_at, quote_received_at) if quote_received_at else None
    )

    if actions:
        if not health.get("trade_allowed"):
            validation_errors.append("actions exist while trade_allowed is false")
        if quote_age is None or quote_age > maximum_age or quote_age < -60:
            validation_errors.append(f"full-market quote age invalid: {quote_age}")
        for action in actions:
            if action.get("action") != "BUY":
                continue
            selected = decision.get("selected_candidate") or {}
            secondary_at = parse_secondary_time(selected.get("secondary_time"))
            if secondary_at is None:
                validation_errors.append("BUY action lacks valid Tencent quote time")
                continue
            completed_dt = datetime.fromisoformat(completed_at)
            secondary_age = (completed_dt - secondary_at).total_seconds()
            if secondary_age > maximum_age or secondary_age < -60:
                validation_errors.append(
                    f"BUY secondary quote age invalid: {secondary_age}"
                )

    snapshot_valid = base_valid and not validation_errors
    snapshot = {
        "schema_version": 1,
        "strategy": account.get("strategy", "周月箱体复利战法2.1"),
        "market_date": health.get("market_date"),
        "locked_at": completed_at,
        "snapshot_valid": snapshot_valid,
        "validation_errors": validation_errors,
        "requested_mode": health.get("requested_mode"),
        "effective_mode": effective_mode,
        "pipeline_ok": health.get("pipeline_ok", health.get("ok")),
        "invariants_ok": health.get("invariants_ok"),
        "trade_allowed": health.get("trade_allowed"),
        "primary_source": health.get("primary_source"),
        "spot_count": health.get("spot_count"),
        "freshness": health.get("freshness"),
        "account": {
            "cash": account.get("cash"),
            "market_value": account.get("market_value"),
            "equity": account.get("equity"),
            "holdings": account.get("holdings"),
            "cycle": account.get("cycle"),
            "realized_pnl": account.get("realized_pnl"),
            "completed_cycles": account.get("completed_cycles"),
        },
        "decision": {
            "cycle_id": decision.get("cycle_id"),
            "cycle_status": decision.get("cycle_status"),
            "trading_days_left": decision.get("trading_days_left"),
            "target_equity": decision.get("target_equity"),
            "gap_to_target": decision.get("gap_to_target"),
            "can_open": decision.get("can_open"),
            "strict_mode": decision.get("strict_mode"),
            "selected_candidate": decision.get("selected_candidate"),
            "actions": actions,
        },
        "candidates": (candidates_payload.get("candidates") or [])[:10],
        "market_summary": market_summary,
    }

    existing = core.load_json(TAIL_SNAPSHOT_PATH, {})
    same_day_valid_existing = bool(
        isinstance(existing, dict)
        and existing.get("market_date") == snapshot.get("market_date")
        and existing.get("snapshot_valid")
    )
    if same_day_valid_existing and not snapshot_valid:
        return
    core.atomic_write_json(TAIL_SNAPSHOT_PATH, snapshot)


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
    completed_at = normalize_completion_timestamps(health, decision, account)
    write_tail_snapshot(health, decision, account, completed_at)
    print(json.dumps({"ok": True, "invariants_ok": True}, ensure_ascii=False))
    return 0


def main() -> int:
    requested_mode = requested_mode_from_argv()
    v2.resolve_effective_mode = safe_resolve_effective_mode
    core.build_candidates = build_candidates_with_fresh_crosscheck
    if requested_mode in {"intraday", "decision", "close"}:
        v2.fetch_full_market = stable_fetch_full_market
    exit_code = v2.main()
    if exit_code != 0:
        return exit_code
    return validate_outputs()


if __name__ == "__main__":
    raise SystemExit(main())
