"""Telegram feed collector for the homepage hot-news panel."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import requests


API_BASE = "https://api.telegram.org"

# 翻译缓存：原文 -> 中文译文，避免重复调用 API
_translation_cache: dict[str, str] = {}


def _extract_text(message: dict[str, Any]) -> str:
    return str(message.get("text") or message.get("caption") or "").strip()


def _is_chinese(text: str) -> bool:
    """判断文本是否已经是中文（超过 30% 汉字）"""
    if not text:
        return False
    han_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return han_count / len(text) > 0.3


def _translate_to_chinese(texts: list[str], api_key: str, groq_key: str = "") -> list[str]:
    """批量翻译为中文，已是中文的直接返回，用缓存避免重复调用。"""
    if not api_key and not groq_key:
        return texts

    results: list[str] = []
    to_translate: list[tuple[int, str]] = []  # (index, text)

    for i, text in enumerate(texts):
        if _is_chinese(text):
            results.append(text)
        elif text in _translation_cache:
            results.append(_translation_cache[text])
        else:
            results.append("")  # 占位，后面填入
            to_translate.append((i, text))

    if not to_translate:
        return results

    try:
        from utils.ai_client import chat

        numbered = "\n\n".join(
            f"[{idx + 1}]\n{text}" for idx, (_, text) in enumerate(to_translate)
        )
        prompt = (
            "将以下新闻消息翻译为简体中文。保留原意，语言简洁自然。"
            "按原编号顺序返回，每条译文前加 [编号]，不要解释。\n\n"
            + numbered
        )

        raw = chat(prompt, api_key_groq=groq_key, api_key_claude=api_key, max_tokens=1024)

        # 解析返回的 [1] 译文... [2] 译文...
        import re
        parts = re.split(r"\[(\d+)\]", raw)
        parsed: dict[int, str] = {}
        for j in range(1, len(parts), 2):
            num = int(parts[j])
            translation = parts[j + 1].strip() if j + 1 < len(parts) else ""
            parsed[num] = translation

        for seq, (orig_idx, orig_text) in enumerate(to_translate):
            translated = parsed.get(seq + 1, orig_text)
            _translation_cache[orig_text] = translated
            results[orig_idx] = translated

    except Exception:
        # 翻译失败时降级为原文
        for orig_idx, orig_text in to_translate:
            results[orig_idx] = orig_text

    return results


def get_recent_messages(
    bot_token: str,
    chat_id: str,
    limit: int = 8,
    claude_api_key: str = "",
    groq_api_key: str = "",
) -> pd.DataFrame:
    """Fetch recent Telegram messages for one chat/channel via Bot API."""
    if not bot_token or not chat_id:
        return pd.DataFrame()

    try:
        response = requests.get(
            f"{API_BASE}/bot{bot_token}/getUpdates",
            params={"limit": 100},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    expected_chat = str(chat_id).strip()

    for update in reversed(payload.get("result", [])):
        message = update.get("message") or update.get("channel_post") or {}
        if not message:
            continue

        message_chat = message.get("chat", {})
        message_chat_id = str(message_chat.get("id", "")).strip()
        message_chat_username = str(message_chat.get("username", "")).strip()
        if expected_chat not in {message_chat_id, message_chat_username}:
            continue

        text = _extract_text(message)
        if not text:
            continue

        created_at = datetime.fromtimestamp(message.get("date", 0))
        rows.append(
            {
                "标题": text.splitlines()[0][:64],
                "内容": text[:240],
                "时间": created_at.strftime("%H:%M"),
                "日期": created_at.strftime("%Y-%m-%d"),
                "来源": message_chat.get("title") or message_chat_username or "Telegram",
            }
        )
        if len(rows) >= limit:
            break

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # 翻译标题和内容（优先 Groq，其次 Claude）
    if groq_api_key or claude_api_key:
        titles = _translate_to_chinese(df["标题"].tolist(), claude_api_key, groq_api_key)
        bodies = _translate_to_chinese(df["内容"].tolist(), claude_api_key, groq_api_key)
        df["标题"] = titles
        df["内容"] = bodies

    return df
