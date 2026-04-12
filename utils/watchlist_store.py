import json
import os


STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".watchlists.json")


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

