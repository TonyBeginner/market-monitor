"""
统一 AI 客户端：优先用 Groq（免费），没有 Groq Key 时降级到 Claude。
"""
from __future__ import annotations

import time


def chat(prompt: str, system: str = "", api_key_groq: str = "", api_key_claude: str = "", max_tokens: int = 2048) -> str:
    """发送一条消息，返回回复文本。自动选择可用的后端。"""
    if api_key_groq:
        try:
            return _groq(prompt, system, api_key_groq, max_tokens)
        except Exception as e:
            # Groq 限流时，优先自动降级到 Claude；否则返回更友好的错误
            if api_key_claude:
                try:
                    return _claude(prompt, system, api_key_claude, max_tokens)
                except Exception:
                    pass
            msg = str(e)
            if "429" in msg or "Too Many Requests" in msg:
                return "AI 服务当前请求过多，请稍后再试。"
            raise
    if api_key_claude:
        return _claude(prompt, system, api_key_claude, max_tokens)
    return ""


def _groq(prompt: str, system: str, api_key: str, max_tokens: int) -> str:
    import requests
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_err = None
    for attempt in range(2):
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": max_tokens},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except requests.HTTPError as e:
            last_err = e
            status = getattr(e.response, "status_code", None)
            if status == 429 and attempt == 0:
                time.sleep(1.2)
                continue
            raise
        except Exception as e:
            last_err = e
            raise
    if last_err:
        raise last_err


def _claude(prompt: str, system: str, api_key: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    kwargs: dict = {"model": "claude-haiku-4-5-20251001", "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    return client.messages.create(**kwargs).content[0].text.strip()
