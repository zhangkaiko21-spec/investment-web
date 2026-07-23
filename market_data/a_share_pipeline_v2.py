#!/usr/bin/env python3
"""Fast and time-safe A-share pipeline for 周月箱体复利战法2.1.

Key design:
1. Intraday/decision runs never refresh bulk daily history.
2. Heavy history maintenance runs only in bootstrap mode and rotates the oldest cache entries.
3. A delayed scheduler can never open a position outside the Beijing tail window.
4. Pipeline health and trading permission are separate states.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
from datetime import datetime, time as dtime
from typing import Any

import a_share_pipeline as core


def market_session(now: datetime, cfg: dict[str, Any]) -> str:
    if not core.is_trading_day(now.date(), cfg):
        return "closed"
    clock = now.time()
    if clock < dtime(9, 15):
        return "pre_open"
    if clock < dtime(9, 30):
        return "call_auction"
    if clock <= dtime(11, 30):
        return "morning"
    if clock < dtime(13, 0):
        return "lunch"
    if clock <= dtime(15, 0):
        return "afternoon"
    return "after_close"


def fetch_full_market() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    statuses: list[dict[str, Any]] = []
    rows, status = core.fetch_spot_eastmoney()
    statuses.append(status.__dict__)
    if not rows:
        rows, status = core.fetch_spot_sina()
        statuses.append(status.__dict__)
    return rows, statuses


def eligible_rows(
    spot_rows: list[dict[str, Any]], cfg: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        row
        for row in spot_rows
        if cfg["min_price"] <= row["price"] <= cfg["max_price"]
        and (row.get("amount") or 0) >= cfg["min_amount"]
        and abs(row.get("pct_change") or 0) < core.limit_pct(row["code"]) - 0.7
    ]


def refresh_history_rotating(
    spot_rows: list[dict[str, Any]],
    cache: dict[str, Any],
    cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Refresh missing/oldest histories instead of repeatedly refreshing the first codes."""
    stocks = cache.setdefault("stocks", {})
    eligible = eligible_rows(spot_rows, cfg)
    limit = int(cfg.get("bootstrap_history_limit", 1200))

    def rank(row: dict[str, Any]) -> tuple[int, str]:
        item = stocks.get(row["code"])
        if not item:
            return (0, "")
        return (1, str(item.get("updated_at") or ""))

    targets = sorted(eligible, key=rank)[:limit]
    refreshed = 0
    errors: list[str] = []

    def worker(row: dict[str, Any]) -> tuple[str, list[dict[str, Any]], str]:
        history, source = core.fetch_history(row["code"], int(cfg["history_days"]))
        return row["code"], history, source

    if targets:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=int(cfg.get("history_workers", 24))
        ) as executor:
            futures = {executor.submit(worker, row): row for row in targets}
            for future in concurrent.futures.as_completed(futures):
                row = futures[future]
                try:
                    code, history, source = future.result()
                    stocks[code] = {
                        "name": row["name"],
                        "source": source,
                        "updated_at": core.now_cn().isoformat(timespec="seconds"),
                        "rows": history,
                    }
                    refreshed += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{row['code']}:{exc}")

    cache["updated_at"] = core.now_cn().isoformat(timespec="seconds")
    return cache, {
        "policy": "rotating_oldest_first",
        "eligible": len(eligible),
        "requested": len(targets),
        "refreshed": refreshed,
        "cached": len(stocks),
        "errors": errors[:20],
    }


def cache_metrics(
    spot_rows: list[dict[str, Any]],
    cache: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    stocks = cache.get("stocks") or {}
    eligible = eligible_rows(spot_rows, cfg)
    eligible_codes = {row["code"] for row in eligible}
    covered = sum(1 for code in eligible_codes if code in stocks)
    return {
        "policy": "read_only_intraday",
        "eligible": len(eligible),
        "requested": 0,
        "refreshed": 0,
        "cached": len(stocks),
        "eligible_covered": covered,
        "coverage_pct": round(covered / len(eligible) * 100, 2) if eligible else 0.0,
        "errors": [],
    }


def resolve_effective_mode(
    requested_mode: str,
    now: datetime,
    account: dict[str, Any],
    cfg: dict[str, Any],
) -> tuple[str, str]:
    """Prevent scheduler delay from creating retroactive buys."""
    if requested_mode == "bootstrap":
        return "bootstrap", "history maintenance"
    if requested_mode == "close":
        return "close", "explicit close mode"
    if requested_mode != "decision":
        return "intraday", "intraday observation"

    forced_close = core.parse_day(account["cycle"]["forced_close"])
    if now.date() >= forced_close and now.time() >= dtime(14, 35):
        return "close", "forced settlement date"
    if (
        core.is_trading_day(now.date(), cfg)
        and dtime(14, 35) <= now.time() <= dtime(14, 58)
    ):
        return "decision", "inside Beijing tail decision window"
    return "intraday", "decision request arrived outside 14:35-14:58 window"


def primary_source(statuses: list[dict[str, Any]]) -> str | None:
    for item in statuses:
        if item.get("ok") and int(item.get("records") or 0) >= 1000:
            return str(item.get("name"))
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["bootstrap", "intraday", "decision", "close"],
        default="intraday",
    )
    args = parser.parse_args()

    cfg = core.load_config()
    core.DATA_DIR.mkdir(parents=True, exist_ok=True)
    core.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    now = core.now_cn()
    timestamp = now.isoformat(timespec="seconds")
    session = market_session(now, cfg)

    spot_rows, sources = fetch_full_market()
    if not spot_rows:
        health = {
            "generated_at": timestamp,
            "market_date": now.date().isoformat(),
            "ok": False,
            "pipeline_ok": False,
            "trade_allowed": False,
            "requested_mode": args.mode,
            "effective_mode": "intraday",
            "market_session": session,
            "spot_count": 0,
            "sources": sources,
            "error": "all full-market spot sources failed",
        }
        core.atomic_write_json(core.DATA_DIR / "health.json", health)
        print(json.dumps(health, ensure_ascii=False))
        return 2

    cache = core.load_json(core.HISTORY_CACHE_PATH, {"stocks": {}})
    if args.mode == "bootstrap":
        cache, history_metrics = refresh_history_rotating(spot_rows, cache, cfg)
        core.atomic_write_json(core.HISTORY_CACHE_PATH, cache)
    else:
        history_metrics = cache_metrics(spot_rows, cache, cfg)

    minimum_history_coverage = int(cfg.get("minimum_history_coverage", 1000))
    history_ready = int(history_metrics.get("cached") or 0) >= minimum_history_coverage

    candidates: list[dict[str, Any]] = []
    tencent_status = core.SourceStatus(
        "tencent_quote", True, 0, timestamp=timestamp
    )
    if history_ready:
        candidates, tencent_status = core.build_candidates(spot_rows, cache, cfg)
    sources.append(tencent_status.__dict__)

    account = core.ensure_account()
    effective_mode, mode_reason = resolve_effective_mode(
        args.mode, now, account, cfg
    )
    if not history_ready:
        effective_mode = "intraday"
        mode_reason = "history cache coverage below safety threshold"

    account, actions, decision_state = core.run_decision_engine(
        account,
        candidates,
        spot_rows,
        cfg,
        effective_mode,
    )

    account["generated_at"] = timestamp
    account["updated_at"] = timestamp
    account["market_date"] = now.date().isoformat()

    decision_window = (
        core.is_trading_day(now.date(), cfg)
        and dtime(14, 35) <= now.time() <= dtime(14, 58)
    )
    forced_close = core.parse_day(account["cycle"]["forced_close"])
    settlement_window = now.date() >= forced_close and now.time() >= dtime(14, 35)
    pipeline_ok = len(spot_rows) >= 1000 and history_ready
    trade_allowed = pipeline_ok and (
        (effective_mode == "decision" and decision_window)
        or (effective_mode == "close" and settlement_window)
    )

    candidate_payload = {
        "generated_at": timestamp,
        "market_date": now.date().isoformat(),
        "requested_mode": args.mode,
        "effective_mode": effective_mode,
        "count": len(candidates),
        "rules": {
            "max_15d_box_pct": cfg["max_15d_box_pct"],
            "max_60d_box_pct": cfg["max_60d_box_pct"],
            "max_position_15d": cfg["max_position_15d"],
            "max_position_60d": cfg["max_position_60d"],
            "min_recovery_score": cfg["min_recovery_score"],
            "min_reward_risk": cfg["min_reward_risk"],
        },
        "candidates": candidates,
    }
    decision_payload = {
        **decision_state,
        "market_date": now.date().isoformat(),
        "requested_mode": args.mode,
        "effective_mode": effective_mode,
        "mode_reason": mode_reason,
        "pipeline_ok": pipeline_ok,
        "trade_allowed": trade_allowed,
        "actions": actions,
        "account_summary": {
            "cash": account["cash"],
            "market_value": account["market_value"],
            "equity": account["equity"],
            "holdings": account["holdings"],
            "cycle": account["cycle"],
        },
        "top_candidates": candidates[:3],
    }

    source_name = primary_source(sources)
    health = {
        "generated_at": timestamp,
        "market_date": now.date().isoformat(),
        "ok": pipeline_ok,
        "pipeline_ok": pipeline_ok,
        "trade_allowed": trade_allowed,
        "requested_mode": args.mode,
        "effective_mode": effective_mode,
        "mode_reason": mode_reason,
        "market_session": session,
        "elapsed_seconds": round(time.time() - started, 2),
        "spot_count": len(spot_rows),
        "candidate_count": len(candidates),
        "primary_source": source_name,
        "sources": sources,
        "history": history_metrics,
        "freshness": {
            "quote_received_at": timestamp,
            "fresh": True,
            "maximum_trade_age_seconds": int(
                cfg.get("maximum_trade_age_seconds", 900)
            ),
        },
        "data_freshness_note": (
            f"本次全市场行情源为{source_name or 'unknown'}；最终候选使用腾讯报价交叉验证。"
            "券商App与公开源冲突时，以券商App为最终执行依据。"
        ),
    }

    core.atomic_write_json(
        core.DATA_DIR / "market_summary.json", core.market_summary(spot_rows)
    )
    core.atomic_write_json(core.DATA_DIR / "candidates.json", candidate_payload)
    core.atomic_write_json(core.DATA_DIR / "decision.json", decision_payload)
    core.atomic_write_json(core.DATA_DIR / "account_state.json", account)
    core.atomic_write_json(core.DATA_DIR / "health.json", health)

    print(
        json.dumps(
            {
                "ok": pipeline_ok,
                "trade_allowed": trade_allowed,
                "requested_mode": args.mode,
                "effective_mode": effective_mode,
                "spot_count": len(spot_rows),
                "candidate_count": len(candidates),
                "actions": actions,
                "equity": account["equity"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if pipeline_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
