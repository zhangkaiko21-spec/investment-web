#!/usr/bin/env python3
"""A-share market data and paper-trading pipeline for 周月箱体复利战法2.1.

The pipeline is intentionally dependency-light and uses multiple public quote
endpoints with timestamp/freshness checks. It never sends real brokerage orders.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import requests

try:
    from chinese_calendar import is_holiday as cn_is_holiday
except Exception:  # pragma: no cover
    cn_is_holiday = None

CN_TZ = ZoneInfo("Asia/Shanghai")
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "a_share"
CONFIG_PATH = ROOT / "market_data" / "strategy_config.json"
ACCOUNT_PATH = DATA_DIR / "account_state.json"
SNAPSHOT_PATH = DATA_DIR / "latest_snapshot.json"
CANDIDATES_PATH = DATA_DIR / "latest_candidates.json"
DECISION_PATH = DATA_DIR / "latest_decision.json"
HEALTH_PATH = DATA_DIR / "health.json"
LEDGER_PATH = DATA_DIR / "ledger.json"

EASTMONEY_SPOT_URL = "https://82.push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
SINA_SPOT_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"})


@dataclass
class SourceStatus:
    name: str
    ok: bool
    rows: int = 0
    error: str | None = None
    timestamp: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "rows": self.rows,
            "error": self.error,
            "timestamp": self.timestamp,
        }


def now_cn() -> datetime:
    return datetime.now(CN_TZ)


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def request_json(url: str, *, params: dict[str, Any] | None = None, timeout: int = 15) -> Any:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = SESSION.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            text = response.text.strip()
            if text.startswith("var ") or text.startswith("v_"):
                raise ValueError("non-json response")
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"request failed: {url}: {last_error}")


def to_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def market_id_for_code(code: str) -> int:
    return 1 if code.startswith(("60", "68")) else 0


def secid_for_code(code: str) -> str:
    return f"{market_id_for_code(code)}.{code}"


def is_a_share(code: str, name: str) -> bool:
    valid_prefix = code.startswith(("00", "30", "60", "68"))
    invalid_name = any(token in name.upper() for token in ("ST", "退", "N ", "C "))
    return len(code) == 6 and valid_prefix and not invalid_name


def fetch_spot_eastmoney() -> tuple[list[dict[str, Any]], SourceStatus]:
    fields = "f12,f14,f2,f3,f4,f5,f6,f7,f8,f10,f15,f16,f17,f18,f20,f21,f13"
    all_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    page_size = 500
    for page in range(1, 15):
        params = {
            "pn": page,
            "pz": page_size,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": fields,
        }
        try:
            payload = request_json(EASTMONEY_SPOT_URL, params=params, timeout=18)
            diff = ((payload or {}).get("data") or {}).get("diff") or []
            if not diff:
                break
            for item in diff:
                code = str(item.get("f12") or "")
                name = str(item.get("f14") or "").strip()
                if not is_a_share(code, name):
                    continue
                price = to_float(item.get("f2"))
                if price is None or price <= 0:
                    continue
                all_rows.append(
                    {
                        "code": code,
                        "name": name,
                        "price": price,
                        "pct_change": to_float(item.get("f3")),
                        "change": to_float(item.get("f4")),
                        "volume": to_float(item.get("f5")),
                        "amount": to_float(item.get("f6")),
                        "amplitude_pct": to_float(item.get("f7")),
                        "turnover_pct": to_float(item.get("f8")),
                        "volume_ratio": to_float(item.get("f10")),
                        "high": to_float(item.get("f15")),
                        "low": to_float(item.get("f16")),
                        "open": to_float(item.get("f17")),
                        "prev_close": to_float(item.get("f18")),
                        "market_cap": to_float(item.get("f20")),
                        "float_market_cap": to_float(item.get("f21")),
                        "market_id": int(item.get("f13") if item.get("f13") is not None else market_id_for_code(code)),
                        "source": "eastmoney",
                        "quote_time": now_cn().isoformat(timespec="seconds"),
                    }
                )
            if len(diff) < page_size:
                break
        except Exception as exc:  # noqa: BLE001
            errors.append(f"page {page}: {exc}")
            if page == 1:
                break
            break
    ok = len(all_rows) >= 1000
    return all_rows if ok else [], SourceStatus(
        "eastmoney_spot",
        ok,
        len(all_rows),
        error=" | ".join(errors)[-1200:] if errors else (None if ok else "insufficient rows"),
        timestamp=now_cn().isoformat(timespec="seconds"),
    )


def fetch_spot_sina() -> tuple[list[dict[str, Any]], SourceStatus]:
    """Fallback full-market source. Sina paginates the hs_a node."""
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    page_size = 100
    for page in range(1, 70):
        params = {
            "page": page,
            "num": page_size,
            "sort": "symbol",
            "asc": 1,
            "node": "hs_a",
            "symbol": "",
            "_s_r_a": "page",
        }
        try:
            payload = request_json(SINA_SPOT_URL, params=params, timeout=16)
            if not isinstance(payload, list):
                raise RuntimeError(f"unexpected payload type: {type(payload).__name__}")
            if not payload:
                break
            for item in payload:
                code = str(item.get("code") or "")
                name = str(item.get("name") or "").strip()
                if not is_a_share(code, name):
                    continue
                price = to_float(item.get("trade"))
                if price is None or price <= 0:
                    continue
                rows.append(
                    {
                        "code": code,
                        "name": name,
                        "price": price,
                        "pct_change": to_float(item.get("changepercent")),
                        "change": to_float(item.get("pricechange")),
                        "volume": to_float(item.get("volume")),
                        "amount": to_float(item.get("amount")),
                        "amplitude_pct": None,
                        "turnover_pct": to_float(item.get("turnoverratio")),
                        "volume_ratio": None,
                        "market_id": 1 if code.startswith(("60", "68")) else 0,
                        "high": to_float(item.get("high")),
                        "low": to_float(item.get("low")),
                        "open": to_float(item.get("open")),
                        "prev_close": to_float(item.get("settlement")),
                        "market_cap": to_float(item.get("mktcap")),
                        "float_market_cap": to_float(item.get("nmc")),
                        "source": "sina",
                        "quote_time": item.get("ticktime"),
                    }
                )
            if len(payload) < page_size:
                break
        except Exception as exc:  # noqa: BLE001
            errors.append(f"page {page}: {exc}")
            if page == 1:
                break
            break
    ok = len(rows) >= 1000
    return rows if ok else [], SourceStatus(
        "sina_spot",
        ok,
        len(rows),
        error=" | ".join(errors)[-1200:] if errors else (None if ok else "insufficient rows"),
        timestamp=now_cn().isoformat(timespec="seconds"),
    )


def fetch_tencent_quotes(codes: Iterable[str]) -> tuple[dict[str, dict[str, Any]], SourceStatus]:
    symbols = [("sh" if code.startswith(("60", "68")) else "sz") + code for code in codes]
    if not symbols:
        return {}, SourceStatus("tencent_quote", True, 0, timestamp=now_cn().isoformat(timespec="seconds"))
    result: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for offset in range(0, len(symbols), 50):
        batch = symbols[offset : offset + 50]
        try:
            response = SESSION.get(TENCENT_QUOTE_URL + ",".join(batch), timeout=12)
            response.raise_for_status()
            response.encoding = "gbk"
            for line in response.text.split(";"):
                if '="' not in line:
                    continue
                left, raw = line.split('="', 1)
                values = raw.rstrip('"').split("~")
                if len(values) < 35:
                    continue
                code = values[2]
                result[code] = {
                    "name": values[1],
                    "price": to_float(values[3]),
                    "prev_close": to_float(values[4]),
                    "open": to_float(values[5]),
                    "volume": to_float(values[6]),
                    "amount": to_float(values[37]) if len(values) > 37 else None,
                    "high": to_float(values[33]) if len(values) > 33 else None,
                    "low": to_float(values[34]) if len(values) > 34 else None,
                    "quote_time": values[30] if len(values) > 30 else None,
                    "source": "tencent",
                }
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
    ok = bool(result)
    return result, SourceStatus(
        "tencent_quote",
        ok,
        len(result),
        error=" | ".join(errors)[-1200:] if errors else None,
        timestamp=now_cn().isoformat(timespec="seconds"),
    )


def fetch_history(code: str, days: int = 120) -> list[dict[str, Any]]:
    end = now_cn().strftime("%Y%m%d")
    start = (now_cn() - timedelta(days=260)).strftime("%Y%m%d")
    params = {
        "secid": secid_for_code(code),
        "klt": 101,
        "fqt": 1,
        "lmt": max(days, 120),
        "beg": start,
        "end": end,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    payload = request_json(EASTMONEY_KLINE_URL, params=params, timeout=15)
    klines = ((payload or {}).get("data") or {}).get("klines") or []
    rows: list[dict[str, Any]] = []
    for raw in klines[-days:]:
        parts = raw.split(",")
        if len(parts) < 11:
            continue
        rows.append(
            {
                "date": parts[0],
                "open": to_float(parts[1]),
                "close": to_float(parts[2]),
                "high": to_float(parts[3]),
                "low": to_float(parts[4]),
                "volume": to_float(parts[5]),
                "amount": to_float(parts[6]),
                "amplitude_pct": to_float(parts[7]),
                "pct_change": to_float(parts[8]),
                "change": to_float(parts[9]),
                "turnover_pct": to_float(parts[10]),
            }
        )
    return rows


def range_width(high: float, low: float) -> float:
    return (high - low) / low if low > 0 else math.inf


def location_ratio(price: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (price - low) / (high - low)))


def recovery_score(history: list[dict[str, Any]], window: int = 60) -> float:
    rows = history[-window:]
    if len(rows) < 20:
        return 0.0
    recovered = 0
    events = 0
    for idx in range(10, len(rows) - 3):
        prior_lows = [r["low"] for r in rows[max(0, idx - 10) : idx] if r.get("low")]
        if not prior_lows:
            continue
        support = statistics.median(prior_lows)
        low = rows[idx].get("low")
        close = rows[idx].get("close")
        if low and close and low < support * 0.985:
            events += 1
            forward = rows[idx : min(len(rows), idx + 5)]
            if any((r.get("close") or 0) >= support for r in forward):
                recovered += 1
    if events == 0:
        return 0.7
    return recovered / events


def analyze_candidate(quote: dict[str, Any], history: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any] | None:
    if len(history) < 60:
        return None
    h15 = history[-15:]
    h60 = history[-60:]
    lows15 = [r["low"] for r in h15 if r.get("low")]
    highs15 = [r["high"] for r in h15 if r.get("high")]
    lows60 = [r["low"] for r in h60 if r.get("low")]
    highs60 = [r["high"] for r in h60 if r.get("high")]
    if not all((lows15, highs15, lows60, highs60)):
        return None
    low15, high15 = min(lows15), max(highs15)
    low60, high60 = min(lows60), max(highs60)
    width15 = range_width(high15, low15)
    width60 = range_width(high60, low60)
    price = quote["price"]
    loc15 = location_ratio(price, low15, high15)
    loc60 = location_ratio(price, low60, high60)
    rec = recovery_score(history)
    amount = quote.get("amount") or 0
    max_width = float(cfg["screening"]["max_box_width_pct"]) / 100
    max_location = float(cfg["screening"]["max_lower_location"])
    min_recovery = float(cfg["screening"]["min_recovery_score"])
    min_amount = float(cfg["screening"]["min_amount_cny"])
    if width15 > max_width or width60 > max_width:
        return None
    if loc15 > max_location or loc60 > 0.55:
        return None
    if rec < min_recovery or amount < min_amount:
        return None
    downside = max(price - max(low15, low60), price * 0.012)
    target = min(high15, high60)
    upside = max(0.0, target - price)
    rr = upside / downside if downside > 0 else 0
    if rr < float(cfg["screening"]["min_reward_risk"]):
        return None
    volume_ratio = quote.get("volume_ratio") or 1.0
    score = (
        (1 - loc15) * 28
        + (1 - loc60) * 20
        + max(0, 1 - width15 / max_width) * 16
        + max(0, 1 - width60 / max_width) * 16
        + rec * 12
        + min(rr, 4) * 2
        + min(max(volume_ratio, 0), 2) * 2
    )
    return {
        "code": quote["code"],
        "name": quote["name"],
        "price": round(price, 3),
        "pct_change": quote.get("pct_change"),
        "amount": amount,
        "source": quote.get("source"),
        "quote_time": quote.get("quote_time"),
        "box_15d": {
            "low": round(low15, 3),
            "high": round(high15, 3),
            "width_pct": round(width15 * 100, 2),
            "location": round(loc15, 3),
        },
        "box_60d": {
            "low": round(low60, 3),
            "high": round(high60, 3),
            "width_pct": round(width60 * 100, 2),
            "location": round(loc60, 3),
        },
        "recovery_score": round(rec, 3),
        "target_price": round(target, 3),
        "stop_price": round(max(low15, low60) * 0.99, 3),
        "upside_pct": round(upside / price * 100, 2),
        "downside_pct": round(downside / price * 100, 2),
        "reward_risk": round(rr, 2),
        "score": round(score, 2),
    }


def load_config() -> dict[str, Any]:
    cfg = read_json(CONFIG_PATH, {})
    if not cfg:
        raise RuntimeError(f"missing config: {CONFIG_PATH}")
    return cfg


def fetch_market_snapshot() -> tuple[list[dict[str, Any]], list[SourceStatus]]:
    statuses: list[SourceStatus] = []
    rows, status = fetch_spot_eastmoney()
    statuses.append(status)
    if rows:
        return rows, statuses
    rows, status = fetch_spot_sina()
    statuses.append(status)
    return rows, statuses


def select_history_universe(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    screening = cfg["screening"]
    min_amount = float(screening["min_amount_cny"])
    max_price = float(screening.get("max_price", 200))
    prefilter = []
    for row in rows:
        price = row.get("price") or 0
        amount = row.get("amount") or 0
        amplitude = abs(row.get("amplitude_pct") or 0)
        pct = abs(row.get("pct_change") or 0)
        if amount < min_amount or price <= 0 or price > max_price:
            continue
        if amplitude > 9.5 or pct > 8.0:
            continue
        prefilter.append(row)
    prefilter.sort(key=lambda r: (abs(r.get("pct_change") or 0), -(r.get("amount") or 0)))
    return prefilter[: int(screening.get("history_prefilter_limit", 280))]


def scan_candidates(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[SourceStatus]]:
    universe = select_history_universe(rows, cfg)
    statuses: list[SourceStatus] = []
    candidates: list[dict[str, Any]] = []
    errors: list[str] = []
    max_workers = int(cfg["screening"].get("history_workers", 12))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_history, row["code"], 120): row for row in universe}
        for future in concurrent.futures.as_completed(futures):
            row = futures[future]
            try:
                analyzed = analyze_candidate(row, future.result(), cfg)
                if analyzed:
                    candidates.append(analyzed)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{row['code']}: {exc}")
    candidates.sort(key=lambda c: c["score"], reverse=True)
    top = candidates[: int(cfg["screening"].get("output_limit", 12))]
    statuses.append(
        SourceStatus(
            "eastmoney_history",
            bool(universe) and (len(errors) < max(10, len(universe) * 0.35)),
            len(universe) - len(errors),
            error=" | ".join(errors[:10]) if errors else None,
            timestamp=now_cn().isoformat(timespec="seconds"),
        )
    )
    if top:
        confirm, status = fetch_tencent_quotes([item["code"] for item in top])
        statuses.append(status)
        for item in top:
            q = confirm.get(item["code"])
            if q and q.get("price"):
                diff = abs(q["price"] - item["price"]) / item["price"]
                item["cross_check"] = {
                    "source": "tencent",
                    "price": q["price"],
                    "quote_time": q.get("quote_time"),
                    "diff_pct": round(diff * 100, 3),
                    "passed": diff <= float(cfg["data_quality"]["max_cross_source_price_diff_pct"]) / 100,
                }
            else:
                item["cross_check"] = {"source": "tencent", "passed": False, "reason": "missing"}
        top = [item for item in top if item["cross_check"].get("passed")]
    return top, statuses


def is_trading_day(day: date, cfg: dict[str, Any]) -> bool:
    if day.weekday() >= 5:
        return False
    if day.isoformat() in set(cfg.get("holidays", [])):
        return False
    if cn_is_holiday is not None:
        try:
            return not bool(cn_is_holiday(day))
        except Exception:
            pass
    return True


def trading_days_between(start: date, end: date, cfg: dict[str, Any]) -> int:
    if end < start:
        return 0
    count = 0
    cursor = start
    while cursor <= end:
        if is_trading_day(cursor, cfg):
            count += 1
        cursor += timedelta(days=1)
    return count


def current_round(account: dict[str, Any]) -> dict[str, Any]:
    rounds = account.get("rounds") or []
    for item in reversed(rounds):
        if item.get("status") == "active":
            return item
    raise RuntimeError("no active round")


def account_metrics(account: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    rnd = current_round(account)
    cash = float(account["cash"])
    holdings_value = sum(float(h.get("market_value") or 0) for h in account.get("holdings", []))
    total = cash + holdings_value
    base = float(rnd["starting_equity"])
    profit = total - base
    return {
        "cash": round(cash, 2),
        "holdings_value": round(holdings_value, 2),
        "total_equity": round(total, 2),
        "round_profit": round(profit, 2),
        "round_return_pct": round(profit / base * 100, 3),
        "target_equity_5pct": round(base * 1.05, 2),
        "gap_to_5pct": round(max(0, base * 1.05 - total), 2),
    }


def compute_position_size(candidate: dict[str, Any], account: dict[str, Any], cfg: dict[str, Any], remaining_days: int) -> dict[str, Any]:
    cash = float(account["cash"])
    if remaining_days <= 3:
        return {"shares": 0, "reason": "within final 3 trading days"}
    exposure = 0.45 if remaining_days <= 5 else 0.65
    max_value = cash * exposure
    shares = int(max_value // (candidate["price"] * 100)) * 100
    if shares < 100:
        return {"shares": 0, "reason": "insufficient cash for 100 shares"}
    return {
        "shares": shares,
        "estimated_value": round(shares * candidate["price"], 2),
        "exposure_pct": round(shares * candidate["price"] / cash * 100, 2),
    }


def create_decision(account: dict[str, Any], candidates: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    today = now_cn().date()
    rnd = current_round(account)
    end = date.fromisoformat(rnd["forced_close_date"])
    remaining_natural = max(0, (end - today).days)
    remaining_trading = trading_days_between(today, end, cfg)
    metrics = account_metrics(account, cfg)
    reached = metrics["round_return_pct"] >= float(cfg["strategy"]["early_target_min_pct"])
    expired = today >= end
    actions: list[dict[str, Any]] = []
    allow_open = not reached and not expired and remaining_trading > 3
    if account.get("holdings"):
        if reached:
            actions.append({"action": "close_all", "reason": "5%-10% target reached"})
        elif expired:
            actions.append({"action": "close_all", "reason": "monthly hard deadline reached"})
    elif allow_open and candidates:
        selected = candidates[0]
        sizing = compute_position_size(selected, account, cfg, remaining_trading)
        if sizing.get("shares", 0) >= 100:
            actions.append(
                {
                    "action": "paper_buy",
                    "code": selected["code"],
                    "name": selected["name"],
                    "reference_price": selected["price"],
                    "shares": sizing["shares"],
                    "stop_price": selected["stop_price"],
                    "target_price": selected["target_price"],
                    "reason": "top candidate satisfies 2.1 box rules",
                    "position": sizing,
                    "requires_next_run_confirmation": True,
                }
            )
    return {
        "generated_at": now_cn().isoformat(timespec="seconds"),
        "round_id": rnd["id"],
        "round_start": rnd["start_date"],
        "forced_close_date": rnd["forced_close_date"],
        "remaining_natural_days": remaining_natural,
        "remaining_trading_days": remaining_trading,
        "metrics": metrics,
        "early_target_reached": reached,
        "deadline_reached": expired,
        "allow_new_position": allow_open,
        "actions": actions,
        "candidate_count": len(candidates),
    }


def validate_data(rows: list[dict[str, Any]], statuses: list[SourceStatus], cfg: dict[str, Any]) -> dict[str, Any]:
    now = now_cn()
    source_ok = any(status.ok and status.rows >= 1000 for status in statuses)
    prices = [r["price"] for r in rows if r.get("price")]
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "source_ok": source_ok,
        "row_count": len(rows),
        "median_price": round(statistics.median(prices), 3) if prices else None,
        "statuses": [status.as_dict() for status in statuses],
        "decision_allowed": source_ok and len(rows) >= int(cfg["data_quality"]["min_market_rows"]),
    }


def update_account_from_pending(account: dict[str, Any], snapshot_map: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    """Execute only decisions written by an earlier run, preserving T+1 semantics."""
    pending = account.get("pending_action")
    if not pending:
        return account
    today = now_cn().date().isoformat()
    if pending.get("created_date") == today:
        return account
    action = pending.get("action")
    fee_cfg = cfg["fees"]
    ledger = account.setdefault("ledger", [])
    if action == "paper_buy":
        quote = snapshot_map.get(pending["code"])
        if not quote:
            return account
        price = float(quote["price"])
        shares = int(pending["shares"])
        gross = price * shares
        commission = max(float(fee_cfg["commission_min"]), gross * float(fee_cfg["commission_rate"]))
        transfer = gross * float(fee_cfg["transfer_fee_rate"])
        total = gross + commission + transfer
        if total <= float(account["cash"]):
            account["cash"] = round(float(account["cash"]) - total, 2)
            account.setdefault("holdings", []).append(
                {
                    "code": pending["code"],
                    "name": pending["name"],
                    "shares": shares,
                    "cost": price,
                    "buy_date": today,
                    "stop_price": pending["stop_price"],
                    "target_price": pending["target_price"],
                    "market_value": round(gross, 2),
                }
            )
            ledger.append(
                {
                    "id": f"buy-{today}-{pending['code']}-{shares}",
                    "date": today,
                    "action": "buy",
                    "code": pending["code"],
                    "shares": shares,
                    "price": price,
                    "fees": round(commission + transfer, 2),
                    "net_cash_change": round(-total, 2),
                }
            )
        account["pending_action"] = None
    return account


def mark_holdings(account: dict[str, Any], snapshot_map: dict[str, dict[str, Any]]) -> None:
    for holding in account.get("holdings", []):
        quote = snapshot_map.get(holding["code"])
        if quote and quote.get("price"):
            holding["last_price"] = quote["price"]
            holding["market_value"] = round(float(quote["price"]) * int(holding["shares"]), 2)
            holding["quote_time"] = quote.get("quote_time")


def maybe_stage_decision(account: dict[str, Any], decision: dict[str, Any]) -> None:
    if account.get("pending_action") or not decision.get("actions"):
        return
    first = decision["actions"][0]
    if first.get("action") == "paper_buy":
        account["pending_action"] = {
            **first,
            "created_at": decision["generated_at"],
            "created_date": decision["generated_at"][:10],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-stage", action="store_true", help="Do not stage a paper order")
    args = parser.parse_args()
    cfg = load_config()
    account = read_json(ACCOUNT_PATH, {})
    if not account:
        raise RuntimeError(f"missing account state: {ACCOUNT_PATH}")
    rows, statuses = fetch_market_snapshot()
    health = validate_data(rows, statuses, cfg)
    write_json(HEALTH_PATH, health)
    if not health["decision_allowed"]:
        snapshot = {
            "generated_at": now_cn().isoformat(timespec="seconds"),
            "data_valid": False,
            "row_count": len(rows),
            "source_status": [s.as_dict() for s in statuses],
            "message": "No reliable full-market source. No paper trade was created.",
        }
        write_json(SNAPSHOT_PATH, snapshot)
        return 2
    snapshot_map = {row["code"]: row for row in rows}
    account = update_account_from_pending(account, snapshot_map, cfg)
    mark_holdings(account, snapshot_map)
    candidates, history_statuses = scan_candidates(rows, cfg)
    statuses.extend(history_statuses)
    snapshot = {
        "generated_at": now_cn().isoformat(timespec="seconds"),
        "data_valid": True,
        "market_rows": len(rows),
        "sources": [s.as_dict() for s in statuses],
        "market_sample": rows[:20],
    }
    decision = create_decision(account, candidates, cfg)
    if not args.no_stage:
        maybe_stage_decision(account, decision)
    account["updated_at"] = now_cn().isoformat(timespec="seconds")
    account["metrics"] = account_metrics(account, cfg)
    write_json(SNAPSHOT_PATH, snapshot)
    write_json(CANDIDATES_PATH, {"generated_at": snapshot["generated_at"], "items": candidates})
    write_json(DECISION_PATH, decision)
    write_json(ACCOUNT_PATH, account)
    write_json(LEDGER_PATH, account.get("ledger", []))
    print(
        json.dumps(
            {
                "ok": True,
                "market_rows": len(rows),
                "candidate_count": len(candidates),
                "decision": decision,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
