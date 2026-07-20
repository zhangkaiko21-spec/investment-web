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

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "a_share"
CACHE_DIR = ROOT / ".cache"
CONFIG_PATH = ROOT / "market_data" / "strategy_config.json"
ACCOUNT_PATH = DATA_DIR / "account_state.json"
HISTORY_CACHE_PATH = CACHE_DIR / "a_share_history.json"

TZ = ZoneInfo("Asia/Shanghai")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
)

EASTMONEY_SPOT_HOSTS = [
    "https://82.push2.eastmoney.com/api/qt/clist/get",
    "https://69.push2.eastmoney.com/api/qt/clist/get",
    "https://push2.eastmoney.com/api/qt/clist/get",
]
EASTMONEY_HISTORY_HOSTS = [
    "https://push2his.eastmoney.com/api/qt/stock/kline/get",
    "https://58.push2his.eastmoney.com/api/qt/stock/kline/get",
]
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
SINA_SPOT_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
TENCENT_HISTORY_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

DEFAULT_CONFIG: dict[str, Any] = {
    "strategy_name": "周月箱体复利战法2.1",
    "commission_rate": 0.0003,
    "minimum_commission": 5.0,
    "stamp_duty_sell": 0.0005,
    "transfer_fee_rate": 0.00001,
    "min_price": 2.0,
    "max_price": 300.0,
    "min_amount": 50_000_000,
    "max_day_amplitude_pct": 9.5,
    "max_15d_box_pct": 15.0,
    "max_60d_box_pct": 15.0,
    "max_position_15d": 0.50,
    "max_position_60d": 0.38,
    "min_recovery_score": 0.60,
    "min_reward_risk": 1.50,
    "min_candidate_score": 72.0,
    "strict_candidate_score": 82.0,
    "normal_allocation": 0.60,
    "strict_allocation": 0.45,
    "candidate_limit": 10,
    "history_days": 90,
    "bootstrap_history_limit": 1200,
    "intraday_missing_history_limit": 180,
    "history_workers": 24,
    "quote_crosscheck_count": 25,
    "price_crosscheck_tolerance_pct": 0.60,
    "no_new_position_days": 3,
    "strict_position_days": 5,
    "holidays": [],
}


def now_cn() -> datetime:
    return datetime.now(TZ)


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def load_config() -> dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(load_json(CONFIG_PATH, {}))
    return cfg


def request_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = 12,
    attempts: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                params=params,
                headers={
                    "User-Agent": USER_AGENT,
                    "Referer": "https://quote.eastmoney.com/",
                    "Accept": "application/json,text/plain,*/*",
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"request failed: {url}: {last_error}")


def to_float(value: Any) -> float | None:
    if value in (None, "-", ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def is_a_share(code: str, name: str) -> bool:
    if len(code) != 6 or not code.isdigit():
        return False
    if not code.startswith(("00", "30", "60", "68", "83", "87", "43", "92")):
        return False
    bad_words = ("ST", "*ST", "退", "B股")
    return not any(word.upper() in name.upper() for word in bad_words)


def market_prefix(code: str) -> str:
    return "sh" if code.startswith(("60", "68")) else "sz"


def secid(code: str) -> str:
    return ("1." if code.startswith(("60", "68")) else "0.") + code


def limit_pct(code: str) -> float:
    if code.startswith(("30", "68")):
        return 20.0
    if code.startswith(("83", "87", "43", "92")):
        return 30.0
    return 10.0


@dataclass
class SourceStatus:
    name: str
    ok: bool
    records: int = 0
    error: str | None = None
    timestamp: str | None = None


def fetch_spot_eastmoney() -> tuple[list[dict[str, Any]], SourceStatus]:
    params = {
        "pn": 1,
        "pz": 6000,
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f6",
        "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
        "fields": (
            "f12,f14,f2,f3,f4,f5,f6,f7,f8,f10,f13,"
            "f15,f16,f17,f18,f20,f21"
        ),
    }
    errors: list[str] = []
    for host in EASTMONEY_SPOT_HOSTS:
        try:
            payload = request_json(host, params=params, timeout=18)
            diff = (((payload or {}).get("data") or {}).get("diff")) or []
            rows: list[dict[str, Any]] = []
            for item in diff:
                code = str(item.get("f12") or "")
                name = str(item.get("f14") or "").strip()
                if not is_a_share(code, name):
                    continue
                price = to_float(item.get("f2"))
                prev_close = to_float(item.get("f18"))
                if price is None or price <= 0:
                    continue
                rows.append(
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
                        "market_id": item.get("f13"),
                        "high": to_float(item.get("f15")),
                        "low": to_float(item.get("f16")),
                        "open": to_float(item.get("f17")),
                        "prev_close": prev_close,
                        "market_cap": to_float(item.get("f20")),
                        "float_market_cap": to_float(item.get("f21")),
                        "source": "eastmoney",
                        "quote_time": now_cn().isoformat(timespec="seconds"),
                    }
                )
            if len(rows) >= 1000:
                return rows, SourceStatus(
                    "eastmoney_spot",
                    True,
                    len(rows),
                    timestamp=now_cn().isoformat(timespec="seconds"),
                )
            errors.append(f"{host}: insufficient records {len(rows)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{host}: {exc}")
    return [], SourceStatus(
        "eastmoney_spot",
        False,
        0,
        error=" | ".join(errors)[-1600:],
        timestamp=now_cn().isoformat(timespec="seconds"),
    )


def fetch_spot_sina() -> tuple[list[dict[str, Any]], SourceStatus]:
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
            payload = request_json(SINA_SPOT_URL, params=params, timeout=15)
            if not isinstance(payload, list):
                raise RuntimeError("unexpected payload type")
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
            break
    ok = len(rows) >= 1000
    return (rows if ok else []), SourceStatus(
        "sina_spot",
        ok,
        len(rows),
        error=" | ".join(errors)[-1600:] if errors else None,
        timestamp=now_cn().isoformat(timespec="seconds"),
    )


def fetch_tencent_quotes(codes: Iterable[str]) -> tuple[dict[str, dict[str, Any]], SourceStatus]:
    symbols = [market_prefix(code) + code for code in codes]
    if not symbols:
        return {}, SourceStatus("tencent_quote", True, 0, timestamp=now_cn().isoformat(timespec="seconds"))
    result: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for offset in range(0, len(symbols), 50):
        batch = symbols[offset : offset + 50]
        try:
            response = requests.get(
                TENCENT_QUOTE_URL + ",".join(batch),
                headers={"User-Agent": USER_AGENT, "Referer": "https://gu.qq.com/"},
                timeout=12,
            )
            response.raise_for_status()
            response.encoding = "gbk"
            for line in response.text.split(";"):
                if '="' not in line:
                    continue
                _, raw = line.split('="', 1)
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
    return result, SourceStatus(
        "tencent_quote",
        bool(result),
        len(result),
        error=" | ".join(errors)[-1000:] if errors else None,
        timestamp=now_cn().isoformat(timespec="seconds"),
    )


def fetch_history_eastmoney(code: str, days: int) -> list[dict[str, Any]]:
    params = {
        "secid": secid(code),
        "klt": 101,
        "fqt": 1,
        "lmt": max(days, 90),
        "end": 20500101,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    errors: list[str] = []
    for host in EASTMONEY_HISTORY_HOSTS:
        try:
            payload = request_json(host, params=params, timeout=12)
            klines = (((payload or {}).get("data") or {}).get("klines")) or []
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
            if len(rows) >= 60:
                return rows
            errors.append(f"{host}: insufficient {len(rows)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{host}: {exc}")
    raise RuntimeError(" | ".join(errors))


def fetch_history_tencent(code: str, days: int) -> list[dict[str, Any]]:
    symbol = market_prefix(code) + code
    params = {"param": f"{symbol},day,,,120,qfq"}
    payload = request_json(TENCENT_HISTORY_URL, params=params, timeout=12)
    data = ((payload or {}).get("data") or {}).get(symbol) or {}
    raw_rows = data.get("qfqday") or data.get("day") or []
    rows: list[dict[str, Any]] = []
    for raw in raw_rows[-days:]:
        if len(raw) < 6:
            continue
        rows.append(
            {
                "date": raw[0],
                "open": to_float(raw[1]),
                "close": to_float(raw[2]),
                "high": to_float(raw[3]),
                "low": to_float(raw[4]),
                "volume": to_float(raw[5]),
                "amount": None,
                "amplitude_pct": None,
                "pct_change": None,
                "change": None,
                "turnover_pct": None,
            }
        )
    if len(rows) < 60:
        raise RuntimeError(f"tencent history insufficient: {len(rows)}")
    return rows


def fetch_history(code: str, days: int) -> tuple[list[dict[str, Any]], str]:
    try:
        return fetch_history_eastmoney(code, days), "eastmoney"
    except Exception:
        return fetch_history_tencent(code, days), "tencent"


def row_box_metrics(rows: list[dict[str, Any]], window: int) -> tuple[float, float, float]:
    sample = rows[-window:]
    highs = [float(row["high"]) for row in sample if row.get("high")]
    lows = [float(row["low"]) for row in sample if row.get("low")]
    if len(highs) < window * 0.8 or len(lows) < window * 0.8:
        raise ValueError("not enough box rows")
    high = max(highs)
    low = min(lows)
    width = (high - low) / low * 100 if low else math.inf
    return low, high, width


def box_position(price: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (price - low) / (high - low)))


def recovery_score(rows: list[dict[str, Any]]) -> float:
    sample = rows[-60:]
    events = 0
    recovered = 0
    for idx in range(10, len(sample) - 3):
        prior = [float(row["low"]) for row in sample[idx - 10 : idx] if row.get("low")]
        low = sample[idx].get("low")
        if not prior or low is None:
            continue
        support = statistics.median(prior)
        if float(low) < support * 0.985:
            events += 1
            forward = sample[idx : min(len(sample), idx + 5)]
            if any((row.get("close") or 0) >= support for row in forward):
                recovered += 1
    return 0.72 if events == 0 else recovered / events


def history_date(rows: list[dict[str, Any]]) -> str | None:
    return rows[-1].get("date") if rows else None


def refresh_history_cache(
    spot_rows: list[dict[str, Any]],
    cache: dict[str, Any],
    cfg: dict[str, Any],
    mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    stocks = cache.setdefault("stocks", {})
    today = now_cn().date().isoformat()
    eligible = [
        row
        for row in spot_rows
        if cfg["min_price"] <= row["price"] <= cfg["max_price"]
        and (row.get("amount") or 0) >= cfg["min_amount"]
        and abs(row.get("pct_change") or 0) < limit_pct(row["code"]) - 0.7
    ]
    if mode == "bootstrap":
        targets = eligible[: int(cfg["bootstrap_history_limit"])]
    else:
        missing = [row for row in eligible if row["code"] not in stocks]
        stale = [
            row
            for row in eligible
            if row["code"] in stocks
            and history_date(stocks[row["code"]].get("rows", [])) != today
        ]
        limit = int(cfg["intraday_missing_history_limit"])
        targets = (missing + stale)[:limit]

    errors: list[str] = []
    refreshed = 0

    def worker(row: dict[str, Any]) -> tuple[str, list[dict[str, Any]], str]:
        rows, source = fetch_history(row["code"], int(cfg["history_days"]))
        return row["code"], rows, source

    if targets:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=int(cfg["history_workers"])
        ) as executor:
            futures = {executor.submit(worker, row): row for row in targets}
            for future in concurrent.futures.as_completed(futures):
                row = futures[future]
                try:
                    code, rows, source = future.result()
                    stocks[code] = {
                        "name": row["name"],
                        "source": source,
                        "updated_at": now_cn().isoformat(timespec="seconds"),
                        "rows": rows,
                    }
                    refreshed += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{row['code']}:{exc}")
    cache["updated_at"] = now_cn().isoformat(timespec="seconds")
    return cache, {
        "eligible": len(eligible),
        "requested": len(targets),
        "refreshed": refreshed,
        "cached": len(stocks),
        "errors": errors[:20],
    }


def build_candidates(
    spot_rows: list[dict[str, Any]], cache: dict[str, Any], cfg: dict[str, Any]
) -> tuple[list[dict[str, Any]], SourceStatus]:
    stocks = cache.get("stocks") or {}
    raw_candidates: list[dict[str, Any]] = []
    for quote in spot_rows:
        item = stocks.get(quote["code"])
        if not item:
            continue
        rows = item.get("rows") or []
        if len(rows) < 60:
            continue
        try:
            low15, high15, width15 = row_box_metrics(rows, 15)
            low60, high60, width60 = row_box_metrics(rows, 60)
        except Exception:
            continue
        price = float(quote["price"])
        pos15 = box_position(price, low15, high15)
        pos60 = box_position(price, low60, high60)
        recovery = recovery_score(rows)
        support = max(low15, low60)
        target = min(high15, high60)
        downside = max(price - support, price * 0.012)
        upside = max(0.0, target - price)
        reward_risk = upside / downside if downside else 0.0
        amplitude = abs(quote.get("amplitude_pct") or 0)
        if not (
            width15 <= cfg["max_15d_box_pct"]
            and width60 <= cfg["max_60d_box_pct"]
            and pos15 <= cfg["max_position_15d"]
            and pos60 <= cfg["max_position_60d"]
            and recovery >= cfg["min_recovery_score"]
            and reward_risk >= cfg["min_reward_risk"]
            and amplitude <= cfg["max_day_amplitude_pct"]
        ):
            continue
        score = (
            (1 - pos15) * 22
            + (1 - pos60) * 22
            + (1 - width15 / cfg["max_15d_box_pct"]) * 15
            + (1 - width60 / cfg["max_60d_box_pct"]) * 15
            + recovery * 15
            + min(reward_risk, 4) / 4 * 8
            + min((quote.get("amount") or 0) / 500_000_000, 1) * 3
        )
        raw_candidates.append(
            {
                "code": quote["code"],
                "name": quote["name"],
                "price": price,
                "pct_change": quote.get("pct_change"),
                "amount": quote.get("amount"),
                "source": quote["source"],
                "quote_time": quote.get("quote_time"),
                "low15": round(low15, 4),
                "high15": round(high15, 4),
                "width15_pct": round(width15, 3),
                "position15": round(pos15, 4),
                "low60": round(low60, 4),
                "high60": round(high60, 4),
                "width60_pct": round(width60, 3),
                "position60": round(pos60, 4),
                "recovery_score": round(recovery, 4),
                "reward_risk": round(reward_risk, 3),
                "target_price": round(target, 4),
                "stop_price": round(support * 0.995, 4),
                "score": round(score, 3),
                "history_source": item.get("source"),
                "history_date": history_date(rows),
                "verified": False,
            }
        )
    raw_candidates.sort(key=lambda row: row["score"], reverse=True)
    crosscheck_codes = [
        row["code"] for row in raw_candidates[: int(cfg["quote_crosscheck_count"])]
    ]
    tencent, status = fetch_tencent_quotes(crosscheck_codes)
    verified: list[dict[str, Any]] = []
    for row in raw_candidates:
        secondary = tencent.get(row["code"])
        if not secondary or not secondary.get("price"):
            continue
        diff = abs(float(secondary["price"]) - row["price"]) / row["price"] * 100
        row["secondary_source"] = "tencent"
        row["secondary_price"] = secondary["price"]
        row["secondary_time"] = secondary.get("quote_time")
        row["price_diff_pct"] = round(diff, 4)
        row["verified"] = diff <= cfg["price_crosscheck_tolerance_pct"]
        if row["verified"]:
            verified.append(row)
        if len(verified) >= int(cfg["candidate_limit"]):
            break
    return verified, status


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


def trading_days_inclusive(start: date, end: date, cfg: dict[str, Any]) -> int:
    if start > end:
        return 0
    total = 0
    cursor = start
    while cursor <= end:
        total += int(is_trading_day(cursor, cfg))
        cursor += timedelta(days=1)
    return total


def previous_trading_day(day: date, cfg: dict[str, Any]) -> date:
    cursor = day
    while not is_trading_day(cursor, cfg):
        cursor -= timedelta(days=1)
    return cursor


def next_trading_day(day: date, cfg: dict[str, Any]) -> date:
    cursor = day + timedelta(days=1)
    while not is_trading_day(cursor, cfg):
        cursor += timedelta(days=1)
    return cursor


def add_one_month(day: date) -> date:
    month = day.month + 1
    year = day.year
    if month == 13:
        year += 1
        month = 1
    month_lengths = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(day.day, month_lengths[month - 1]))


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def calculate_fees(gross: float, side: str, cfg: dict[str, Any]) -> float:
    commission = max(cfg["minimum_commission"], gross * cfg["commission_rate"])
    transfer = gross * cfg["transfer_fee_rate"]
    stamp = gross * cfg["stamp_duty_sell"] if side == "SELL" else 0.0
    return round(commission + transfer + stamp, 2)


def trade_id(action: str, code: str, timestamp: str, price: float, shares: int) -> str:
    return f"{timestamp[:10]}-{action}-{code}-{shares}-{price:.4f}"


def append_trade(account: dict[str, Any], trade: dict[str, Any]) -> None:
    ids = {item.get("id") for item in account.setdefault("trades", [])}
    if trade["id"] not in ids:
        account["trades"].append(trade)


def mark_equity(account: dict[str, Any], spot_by_code: dict[str, dict[str, Any]]) -> float:
    market_value = 0.0
    for holding in account.get("holdings", []):
        quote = spot_by_code.get(holding["code"])
        price = quote["price"] if quote else holding.get("last_price", holding["cost"])
        holding["last_price"] = price
        holding["market_value"] = round(price * int(holding["shares"]), 2)
        market_value += holding["market_value"]
    account["market_value"] = round(market_value, 2)
    account["equity"] = round(float(account["cash"]) + market_value, 2)
    return account["equity"]


def sell_holding(
    account: dict[str, Any],
    holding: dict[str, Any],
    price: float,
    reason: str,
    cfg: dict[str, Any],
    timestamp: str,
) -> dict[str, Any]:
    shares = int(holding["shares"])
    gross = round(price * shares, 2)
    fees = calculate_fees(gross, "SELL", cfg)
    net = round(gross - fees, 2)
    cost_basis = round(float(holding["cost"]) * shares + float(holding.get("buy_fees", 0)), 2)
    pnl = round(net - cost_basis, 2)
    account["cash"] = round(float(account["cash"]) + net, 2)
    trade = {
        "id": trade_id("SELL", holding["code"], timestamp, price, shares),
        "timestamp": timestamp,
        "action": "SELL",
        "code": holding["code"],
        "name": holding["name"],
        "shares": shares,
        "price": round(price, 4),
        "gross": gross,
        "fees": fees,
        "net_cash": net,
        "realized_pnl": pnl,
        "reason": reason,
    }
    append_trade(account, trade)
    return trade


def buy_candidate(
    account: dict[str, Any],
    candidate: dict[str, Any],
    allocation: float,
    cfg: dict[str, Any],
    timestamp: str,
) -> dict[str, Any] | None:
    price = float(candidate["price"])
    available = float(account["cash"]) * allocation
    shares = int(available // (price * 100)) * 100
    if shares < 100:
        return None
    gross = round(price * shares, 2)
    fees = calculate_fees(gross, "BUY", cfg)
    if gross + fees > float(account["cash"]):
        return None
    account["cash"] = round(float(account["cash"]) - gross - fees, 2)
    target_price = min(
        float(candidate["target_price"]),
        price * 1.035,
    )
    stop_price = max(
        float(candidate["low60"]) * 0.995,
        price * 0.97,
    )
    holding = {
        "code": candidate["code"],
        "name": candidate["name"],
        "shares": shares,
        "cost": round(price, 4),
        "buy_fees": fees,
        "buy_time": timestamp,
        "target_price": round(target_price, 4),
        "stop_price": round(stop_price, 4),
        "source_candidate_score": candidate["score"],
        "breach_count": 0,
    }
    account.setdefault("holdings", []).append(holding)
    trade = {
        "id": trade_id("BUY", candidate["code"], timestamp, price, shares),
        "timestamp": timestamp,
        "action": "BUY",
        "code": candidate["code"],
        "name": candidate["name"],
        "shares": shares,
        "price": round(price, 4),
        "gross": gross,
        "fees": fees,
        "net_cash": round(-(gross + fees), 2),
        "reason": "箱体下沿候选，符合周月箱体复利战法2.1",
        "candidate_score": candidate["score"],
        "target_price": round(target_price, 4),
        "stop_price": round(stop_price, 4),
    }
    append_trade(account, trade)
    return trade


def roll_cycle(account: dict[str, Any], cfg: dict[str, Any], today: date, reason: str) -> None:
    cycle = account["cycle"]
    closed = {
        "cycle_id": cycle["id"],
        "start": cycle["start"],
        "forced_close": cycle["forced_close"],
        "closed_at": today.isoformat(),
        "reason": reason,
        "ending_equity": account["equity"],
        "return_pct": round(
            (account["equity"] / float(cycle["starting_capital"]) - 1) * 100, 4
        ),
    }
    account.setdefault("completed_cycles", []).append(closed)
    next_start = next_trading_day(today, cfg)
    nominal_end = add_one_month(next_start)
    forced_close = previous_trading_day(nominal_end, cfg)
    account["cycle"] = {
        "id": int(cycle["id"]) + 1,
        "start": next_start.isoformat(),
        "forced_close": forced_close.isoformat(),
        "starting_capital": account["equity"],
        "target_min": cycle.get("target_min", 0.05),
        "target_max": cycle.get("target_max", 0.10),
        "status": "scheduled",
    }


def run_decision_engine(
    account: dict[str, Any],
    candidates: list[dict[str, Any]],
    spot_rows: list[dict[str, Any]],
    cfg: dict[str, Any],
    mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    timestamp = now_cn().isoformat(timespec="seconds")
    today = now_cn().date()
    spot_by_code = {row["code"]: row for row in spot_rows}
    equity = mark_equity(account, spot_by_code)
    cycle = account["cycle"]
    cycle_start = parse_day(cycle["start"])
    forced_close = parse_day(cycle["forced_close"])
    if today < cycle_start:
        cycle["status"] = "scheduled"
    else:
        cycle["status"] = "active"
    days_left = trading_days_inclusive(today, forced_close, cfg)
    natural_days_left = max(0, (forced_close - today).days)
    target_equity = round(float(cycle["starting_capital"]) * (1 + float(cycle["target_min"])), 2)
    gap = round(target_equity - equity, 2)
    actions: list[dict[str, Any]] = []

    decision_allowed = mode in {"decision", "close"} and today >= cycle_start and is_trading_day(today, cfg)

    if decision_allowed and account.get("holdings"):
        remaining: list[dict[str, Any]] = []
        for holding in account["holdings"]:
            quote = spot_by_code.get(holding["code"])
            if not quote:
                remaining.append(holding)
                continue
            price = float(quote["price"])
            reason: str | None = None
            if today >= forced_close:
                reason = "本轮到期强制结算"
            elif price >= float(holding["target_price"]):
                reason = "达到预设箱体止盈价"
            elif mode == "decision" and price < float(holding["stop_price"]):
                reason = "尾盘跌破止损位"
            if reason:
                actions.append(
                    sell_holding(account, holding, price, reason, cfg, timestamp)
                )
            else:
                remaining.append(holding)
        account["holdings"] = remaining
        equity = mark_equity(account, spot_by_code)
        gap = round(target_equity - equity, 2)

    reached_target = equity >= target_equity
    if decision_allowed and reached_target:
        if account.get("holdings"):
            remaining = []
            for holding in account["holdings"]:
                quote = spot_by_code.get(holding["code"])
                if quote:
                    actions.append(
                        sell_holding(
                            account,
                            holding,
                            float(quote["price"]),
                            "账户达到本轮最低收益目标，锁定成果",
                            cfg,
                            timestamp,
                        )
                    )
                else:
                    remaining.append(holding)
            account["holdings"] = remaining
            equity = mark_equity(account, spot_by_code)
        if not account.get("holdings") and account["cycle"]["status"] == "active":
            roll_cycle(account, cfg, today, "提前达到收益目标")
            account["cycle"]["status"] = "scheduled"

    cycle = account["cycle"]
    if cycle["status"] == "active" and today >= parse_day(cycle["forced_close"]):
        if not account.get("holdings"):
            roll_cycle(account, cfg, today, "到期结算")
            account["cycle"]["status"] = "scheduled"

    cycle = account["cycle"]
    cycle_start = parse_day(cycle["start"])
    forced_close = parse_day(cycle["forced_close"])
    days_left = trading_days_inclusive(today, forced_close, cfg) if today >= cycle_start else 0
    natural_days_left = max(0, (forced_close - today).days)
    equity = mark_equity(account, spot_by_code)
    target_equity = round(float(cycle["starting_capital"]) * (1 + float(cycle["target_min"])), 2)
    gap = round(target_equity - equity, 2)

    can_open = (
        decision_allowed
        and cycle["status"] == "active"
        and not account.get("holdings")
        and gap > 0
        and days_left > int(cfg["no_new_position_days"])
    )
    strict_mode = days_left <= int(cfg["strict_position_days"])
    selected: dict[str, Any] | None = None
    if can_open:
        threshold = cfg["strict_candidate_score"] if strict_mode else cfg["min_candidate_score"]
        for candidate in candidates:
            if candidate["score"] < threshold:
                continue
            if not candidate.get("verified"):
                continue
            if strict_mode and (
                candidate["position60"] > 0.28
                or candidate["reward_risk"] < 2.0
            ):
                continue
            selected = candidate
            break
        if selected:
            allocation = (
                cfg["strict_allocation"] if strict_mode else cfg["normal_allocation"]
            )
            trade = buy_candidate(account, selected, allocation, cfg, timestamp)
            if trade:
                actions.append(trade)
                equity = mark_equity(account, spot_by_code)

    account["updated_at"] = timestamp
    account["market_date"] = today.isoformat()
    account["realized_pnl"] = round(
        float(account.get("locked_realized_pnl", 457.53))
        + sum(float(t.get("realized_pnl") or 0) for t in account.get("trades", [])),
        2,
    )
    current_cycle = account["cycle"]
    state = {
        "generated_at": timestamp,
        "mode": mode,
        "cycle_id": current_cycle["id"],
        "cycle_status": current_cycle["status"],
        "cycle_start": current_cycle["start"],
        "forced_close": current_cycle["forced_close"],
        "natural_days_left": natural_days_left,
        "trading_days_left": days_left,
        "equity": account["equity"],
        "target_equity": target_equity,
        "gap_to_target": gap,
        "target_reached": account["equity"] >= target_equity,
        "deadline_reached": today >= forced_close,
        "can_open": can_open,
        "strict_mode": strict_mode,
        "selected_candidate": selected,
    }
    return account, actions, state


def compact(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": row["code"],
        "name": row["name"],
        "price": row["price"],
        "pct_change": row.get("pct_change"),
        "amount": row.get("amount"),
    }


def market_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    changes = [row for row in rows if row.get("pct_change") is not None]
    up = sum(1 for row in changes if row["pct_change"] > 0)
    down = sum(1 for row in changes if row["pct_change"] < 0)
    flat = len(changes) - up - down
    amount = sum(float(row.get("amount") or 0) for row in rows)
    top_up = sorted(changes, key=lambda row: row["pct_change"], reverse=True)[:10]
    top_down = sorted(changes, key=lambda row: row["pct_change"])[:10]
    return {
        "generated_at": now_cn().isoformat(timespec="seconds"),
        "stocks": len(rows),
        "up": up,
        "down": down,
        "flat": flat,
        "total_amount": round(amount, 2),
        "top_gainers": [compact(row) for row in top_up],
        "top_losers": [compact(row) for row in top_down],
    }


def ensure_account() -> dict[str, Any]:
    default = {
        "strategy": "周月箱体复利战法2.1",
        "initial_capital": 10000.0,
        "cash": 10457.53,
        "market_value": 0.0,
        "equity": 10457.53,
        "holdings": [],
        "cycle": {
            "id": 1,
            "start": "2026-06-26",
            "forced_close": "2026-07-24",
            "starting_capital": 10000.0,
            "target_min": 0.05,
            "target_max": 0.10,
            "status": "active",
        },
        "locked_trades": [
            {
                "code": "000651",
                "name": "格力电器",
                "action": "SELL",
                "shares": 100,
                "price": 39.06,
                "net_cash": 3897.05,
                "reason": "第一档止盈，已锁定，不得重复",
            },
            {
                "code": "600887",
                "name": "伊利股份",
                "action": "SELL",
                "shares": 100,
                "price": 25.30,
                "net_cash": 2523.63,
                "reason": "止盈，已锁定，不得重复",
            },
            {
                "code": "000651",
                "name": "格力电器",
                "action": "SELL",
                "shares": 100,
                "price": 39.20,
                "net_cash": 3912.94,
                "reason": "第二档止盈，已锁定，不得重复",
            },
        ],
        "trades": [],
        "completed_cycles": [],
        "locked_realized_pnl": 457.53,
        "realized_pnl": 457.53,
        "updated_at": "2026-07-16T15:00:00+08:00",
    }
    account = load_json(ACCOUNT_PATH, default)
    for key, value in default.items():
        account.setdefault(key, value)
    return account


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["bootstrap", "intraday", "decision", "close"],
        default="intraday",
    )
    args = parser.parse_args()
    cfg = load_config()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    sources: list[dict[str, Any]] = []
    spot_rows, spot_status = fetch_spot_eastmoney()
    sources.append(spot_status.__dict__)
    if not spot_rows:
        spot_rows, sina_status = fetch_spot_sina()
        sources.append(sina_status.__dict__)
    if not spot_rows:
        health = {
            "generated_at": now_cn().isoformat(timespec="seconds"),
            "ok": False,
            "mode": args.mode,
            "sources": sources,
            "error": "all full-market spot sources failed",
        }
        atomic_write_json(DATA_DIR / "health.json", health)
        print(json.dumps(health, ensure_ascii=False))
        return 2

    cache = load_json(HISTORY_CACHE_PATH, {"stocks": {}})
    cache, history_metrics = refresh_history_cache(
        spot_rows, cache, cfg, args.mode
    )
    atomic_write_json(HISTORY_CACHE_PATH, cache)

    candidates, tencent_status = build_candidates(spot_rows, cache, cfg)
    sources.append(tencent_status.__dict__)
    account = ensure_account()
    account, actions, decision_state = run_decision_engine(
        account, candidates, spot_rows, cfg, args.mode
    )

    candidate_payload = {
        "generated_at": now_cn().isoformat(timespec="seconds"),
        "mode": args.mode,
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
    health = {
        "generated_at": now_cn().isoformat(timespec="seconds"),
        "ok": True,
        "mode": args.mode,
        "elapsed_seconds": round(time.time() - started, 2),
        "spot_count": len(spot_rows),
        "candidate_count": len(candidates),
        "sources": sources,
        "history": history_metrics,
        "data_freshness_note": (
            "实时价来自东财并对最终候选使用腾讯行情交叉验证；"
            "券商App与公开源冲突时，以券商App为最终执行依据。"
        ),
    }

    atomic_write_json(DATA_DIR / "market_summary.json", market_summary(spot_rows))
    atomic_write_json(DATA_DIR / "candidates.json", candidate_payload)
    atomic_write_json(DATA_DIR / "decision.json", decision_payload)
    atomic_write_json(DATA_DIR / "account_state.json", account)
    atomic_write_json(DATA_DIR / "health.json", health)

    print(
        json.dumps(
            {
                "ok": True,
                "mode": args.mode,
                "spot_count": len(spot_rows),
                "candidate_count": len(candidates),
                "actions": actions,
                "equity": account["equity"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
