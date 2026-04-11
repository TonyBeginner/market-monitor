"""Persist daily briefs to the GitHub repo so they survive Streamlit Cloud restarts."""
from __future__ import annotations

import base64
import requests

REPO = "TonyBeginner/market-monitor"
BRANCH = "main"
_API = "https://api.github.com"
_RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"


def read_brief(date_str: str) -> tuple[str, str]:
    """Return (content, time_str) for the given date, or ('', '') if not found."""
    url = f"{_RAW}/briefs/{date_str}.md"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return "", ""
        text = r.text
        lines = text.splitlines()
        if lines and lines[0].startswith("<!-- generated:"):
            time_str = lines[0].replace("<!-- generated:", "").replace("-->", "").strip()
            content = "\n".join(lines[1:]).strip()
            return content, time_str
        return text, ""
    except Exception:
        return "", ""


def write_brief(date_str: str, content: str, time_str: str, token: str) -> bool:
    """Commit the brief to briefs/{date_str}.md in the repo. Returns True on success."""
    if not token:
        return False

    path = f"briefs/{date_str}.md"
    url = f"{_API}/repos/{REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    full_text = f"<!-- generated: {time_str} -->\n{content}"
    encoded = base64.b64encode(full_text.encode("utf-8")).decode("utf-8")

    # Fetch existing SHA (required for updates)
    sha: str | None = None
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            sha = resp.json().get("sha")
    except Exception:
        pass

    payload: dict = {
        "message": f"auto: morning brief {date_str}",
        "content": encoded,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(url, json=payload, headers=headers, timeout=30)
        return r.status_code in (200, 201)
    except Exception:
        return False
