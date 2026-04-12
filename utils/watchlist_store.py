import json
import os
from copy import deepcopy


STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".watchlists.json")

POSITION_FIELDS = ["market", "symbol", "name", "quantity", "cost", "note"]
MONITOR_ORDER_KEY = "watchlist_monitor_order"


def _load_all() -> dict:
    if not os.path.exists(STORE_PATH):
        return {}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_all(data: dict) -> None:
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _normalize_symbols(symbols: list[str]) -> list[str]:
    result = []
    seen = set()
    for sym in symbols:
        norm = str(sym or "").strip().upper()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        result.append(norm)
    return result


def _normalize_position(item: dict) -> dict:
    row = dict(item or {})
    symbol = str(row.get("symbol", "") or "").strip().upper()
    market = str(row.get("market", "") or "").strip()
    name = str(row.get("name", "") or "").strip()
    note = str(row.get("note", "") or "").strip()

    try:
        quantity = float(row.get("quantity", 0) or 0)
    except Exception:
        quantity = 0.0

    try:
        cost = float(row.get("cost", 0) or 0)
    except Exception:
        cost = 0.0

    return {
        "market": market,
        "symbol": symbol,
        "name": name,
        "quantity": quantity,
        "cost": cost,
        "note": note,
    }


def _normalize_positions(items: list[dict]) -> list[dict]:
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_position(item)
        if not normalized["market"] or not normalized["symbol"]:
            continue
        result.append(normalized)
    return result


def get_watchlist(name: str, default: list[str]) -> list[str]:
    data = _load_all()
    stored = data.get(name)
    if not isinstance(stored, list) or not stored:
        return _normalize_symbols(default)
    return _normalize_symbols(stored)


def save_watchlist(name: str, symbols: list[str]) -> list[str]:
    data = _load_all()
    cleaned = _normalize_symbols(symbols)
    data[name] = cleaned
    _save_all(data)
    return cleaned


def get_all_watchlists(defaults: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    defaults = defaults or {}
    data = _load_all()
    result = {}
    keys = set(defaults.keys()) | {"us", "cn", "intl_futures", "cn_futures"}
    for key in keys:
        stored = data.get(key)
        if isinstance(stored, list) and stored:
            result[key] = _normalize_symbols(stored)
        else:
            result[key] = _normalize_symbols(defaults.get(key, []))
    return result


def save_watchlists(items: dict[str, list[str]]) -> dict[str, list[str]]:
    data = _load_all()
    result = {}
    for key, symbols in (items or {}).items():
        cleaned = _normalize_symbols(symbols)
        data[key] = cleaned
        result[key] = cleaned
    _save_all(data)
    return result


def get_positions() -> list[dict]:
    data = _load_all()
    stored = data.get("positions")
    if not isinstance(stored, list):
        return []
    return _normalize_positions(stored)


def save_positions(items: list[dict]) -> list[dict]:
    data = _load_all()
    cleaned = _normalize_positions(items)
    data["positions"] = cleaned
    _save_all(data)
    return cleaned


def upsert_position(item: dict, index: int | None = None) -> list[dict]:
    items = get_positions()
    normalized = _normalize_position(item)
    if index is None:
        items.append(normalized)
    elif 0 <= index < len(items):
        items[index] = normalized
    else:
        items.append(normalized)
    return save_positions(items)


def delete_position(index: int) -> list[dict]:
    items = get_positions()
    if 0 <= index < len(items):
        del items[index]
    return save_positions(items)


def export_store_snapshot() -> dict:
    data = _load_all()
    return deepcopy(data)


def get_watchlist_monitor_order() -> list[str]:
    data = _load_all()
    stored = data.get(MONITOR_ORDER_KEY)
    if not isinstance(stored, list):
        return []
    result = []
    seen = set()
    for item in stored:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def save_watchlist_monitor_order(items: list[str]) -> list[str]:
    data = _load_all()
    cleaned = []
    seen = set()
    for item in items or []:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(key)
    data[MONITOR_ORDER_KEY] = cleaned
    _save_all(data)
    return cleaned

