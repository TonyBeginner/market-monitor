"""
配置文件
Key 优先从 Streamlit Secrets 读取（部署环境），
本地开发时从 .streamlit/secrets.toml 读取，
也可以直接在下方填写（仅限本地，不要提交到 GitHub）
"""
import os

def _get_secret(key: str, fallback: str = "") -> str:
    """优先读取 Streamlit secrets，其次读取环境变量，最后用 fallback"""
    try:
        import streamlit as st
        secrets = getattr(st, "secrets", None)
        if secrets is not None:
            try:
                return str(secrets[key])
            except KeyError:
                pass
            except Exception:
                pass
    except Exception:
        pass
    return os.environ.get(key, fallback) or fallback

# ─── Claude API Key ──────────────────────────────────────────────
CLAUDE_API_KEY = _get_secret("CLAUDE_API_KEY")

# ─── GitHub Token（用于持久化存储每日早报）────────────────────────
GITHUB_TOKEN = _get_secret("GITHUB_TOKEN")

# ─── Tushare Pro Token ───────────────────────────────────────────
TUSHARE_TOKEN = _get_secret("TUSHARE_TOKEN")
TELEGRAM_BOT_TOKEN = _get_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _get_secret("TELEGRAM_CHAT_ID")

# ─── 刷新间隔（秒）──────────────────────────────────────────────
REFRESH_INTERVAL = 30   # 默认30秒刷新一次

# ─── 自选股列表（美股）──────────────────────────────────────────
# 直接填 Yahoo Finance 代码即可
MY_US_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA",
    "BABA", "PDD",
]

# ─── 自选股列表（A股）───────────────────────────────────────────
# 格式：Tushare ts_code，如 600519.SH
MY_CN_WATCHLIST = [
    "600519.SH",   # 贵州茅台
    "000858.SZ",   # 五粮液
    "601318.SH",   # 中国平安
    "600036.SH",   # 招商银行
    "002594.SZ",   # 比亚迪
]

# ─── 期货关注分类 ────────────────────────────────────────────────
# 可选: 能源 / 贵金属 / 工业金属 / 农产品 / 股指
MY_FUTURES_CATEGORIES = ["能源", "贵金属", "工业金属", "股指"]
