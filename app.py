"""
全球金融市场监控平台 - 主应用
运行方式: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import base64
import html as html_lib
import json
from urllib.parse import quote
import time
import sys
import os
import shutil
import re

# 确保模块路径正确
sys.path.insert(0, os.path.dirname(__file__))

import config
from collectors import us_stocks, cn_stocks, futures, telegram_feed
from agents import morning_brief as ai_brief
from utils import ai_client, github_store, disk_cache
from utils import watchlist_store

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

try:
    from st_keyup import st_keyup
except Exception:
    st_keyup = None


@st.cache_resource
def backup_watchlists_on_startup() -> str:
    src = os.path.join(os.path.dirname(__file__), ".watchlists.json")
    if not os.path.exists(src):
        return ""
    backup_dir = os.path.join(os.path.dirname(__file__), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(backup_dir, f".watchlists_{timestamp}.json")
    try:
        shutil.copy2(src, dst)
        return dst
    except Exception as e:
        print(f"[Backup] 启动备份失败: {e}")
        return ""


backup_watchlists_on_startup()

# ─── 页面配置 ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="全球金融市场监控",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 自定义样式 ───────────────────────────────────────────────────
st.markdown("""
<style>
    :root {
        --bg: #05080d;
        --panel: rgba(10, 16, 28, 0.88);
        --panel-strong: rgba(14, 23, 38, 0.96);
        --ink: #eaf2ff;
        --muted: #8ea3bd;
        --line: rgba(110, 170, 255, 0.14);
        --gold: #7bc7ff;
        --gold-soft: rgba(73, 198, 255, 0.12);
        --rise: #38f28b;
        --fall: #ff6257;
        --navy: #dfe9f8;
    }
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(73, 198, 255, 0.12), transparent 24%),
            radial-gradient(circle at top right, rgba(255, 98, 87, 0.08), transparent 20%),
            linear-gradient(180deg, #07111b 0%, #05080d 38%, #04070b 100%);
        color: var(--ink);
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1380px;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #11273b 0%, #17324a 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    [data-testid="stSidebar"] * {
        color: #eef3f7;
    }
    .sidebar-brand {
        padding: 1rem 1rem 0.9rem 1rem;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        background: linear-gradient(135deg, rgba(255,255,255,0.07), rgba(73,198,255,0.03));
        margin-bottom: 0.75rem;
        box-shadow: 0 0 0 1px rgba(73,198,255,0.04), 0 14px 36px rgba(0,0,0,0.28);
    }
    .sidebar-kicker {
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: #d8b26a;
        margin-bottom: 0.35rem;
    }
    .sidebar-title {
        font-size: 1.4rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .sidebar-subtitle {
        color: rgba(238,243,247,0.72);
        font-size: 0.9rem;
        margin-top: 0.35rem;
    }
    .hero-panel {
        padding: 1.3rem 1.4rem;
        border-radius: 16px;
        border: 1px solid var(--line);
        background:
            linear-gradient(135deg, rgba(12, 19, 31, 0.96), rgba(7, 11, 18, 0.98)),
            linear-gradient(120deg, rgba(73, 198, 255, 0.04), rgba(255, 98, 87, 0.02));
        box-shadow: 0 14px 32px rgba(0, 0, 0, 0.34);
        margin-bottom: 1rem;
    }
    .hero-kicker {
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: rgba(123, 199, 255, 0.78);
        margin-bottom: 0.45rem;
        font-weight: 700;
    }
    .hero-title {
        font-size: 1.72rem;
        font-weight: 800;
        line-height: 1.1;
        color: #edf4ff;
        margin-bottom: 0.5rem;
    }
    .hero-text {
        color: rgba(142, 163, 189, 0.86);
        font-size: 0.92rem;
        max-width: 780px;
    }
    .status-strip {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.85rem;
        margin: 0.4rem 0 1.1rem 0;
    }
    .status-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1rem 1.05rem;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22);
    }
    .status-label {
        color: var(--muted);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.35rem;
    }
    .status-value {
        color: #f2f7ff;
        font-size: 1.25rem;
        font-weight: 800;
    }
    .status-note {
        color: var(--muted);
        font-size: 0.84rem;
        margin-top: 0.28rem;
    }
    .micro-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 0.35rem;
    }
    .micro-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.48rem 0.72rem;
        border-radius: 999px;
        background: rgba(17, 29, 48, 0.82);
        border: 1px solid var(--line);
        color: var(--muted);
        font-size: 0.84rem;
    }
    .micro-dot {
        width: 0.52rem;
        height: 0.52rem;
        border-radius: 50%;
        display: inline-block;
    }
    .section-title {
        font-size: 0.72rem;
        font-weight: 800;
        color: rgba(123, 199, 255, 0.82);
        text-transform: uppercase;
        letter-spacing: 0.18em;
        padding: 0;
        border-bottom: none;
        margin: 1rem 0 0.7rem 0;
    }
    .section-panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1rem 1rem 0.8rem 1rem;
        box-shadow: 0 14px 34px rgba(0, 0, 0, 0.24);
        margin-bottom: 1rem;
    }
    .metric-up   { color: var(--rise); font-weight: bold; }
    .metric-down { color: var(--fall); font-weight: bold; }
    .metric-flat { color: var(--muted); }
    .m-card {
        background: linear-gradient(180deg, rgba(16, 26, 43, 0.96), rgba(10, 16, 28, 0.98));
        border-radius: 16px;
        padding: 0.7rem 0.8rem 0.75rem 0.8rem;
        border: 1px solid var(--line);
        box-shadow: 0 12px 26px rgba(0,0,0,0.22);
        margin-bottom: 0.5rem;
        height: 108px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .m-label {
        font-size: 0.78rem;
        color: var(--muted);
        letter-spacing: 0.02em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    /* 可点击卡片悬停效果 */
    .m-card.clickable:hover {
        border-color: rgba(73,198,255,0.4) !important;
        cursor: pointer !important;
    }
    .m-value {
        font-weight: 700;
        line-height: 1.1;
        letter-spacing: -0.01em;
        white-space: nowrap;
        overflow: hidden;
    }
    .m-badge {
        display: inline-block;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
    }
    .m-badge.up   { background: rgba(56, 242, 139, 0.15); color: var(--rise); }
    .m-badge.down { background: rgba(255, 98,  87, 0.15); color: var(--fall); }
    .m-badge.flat { background: rgba(130,150,180, 0.12); color: var(--muted); }
    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid var(--line);
    }
    .stDataFrame thead th {
        background-color: #101a2b !important;
        color: #eaf2ff !important;
        border: none !important;
    }
    .stDataFrame tbody tr:nth-child(even) td {
        background: rgba(14, 23, 38, 0.82) !important;
    }
    .stDataFrame tbody tr:nth-child(odd) td {
        background: rgba(10, 16, 28, 0.94) !important;
    }
    .stDataFrame td {
        color: #dce7f7 !important;
        border-color: rgba(110, 170, 255, 0.06) !important;
    }
    .stButton > button, .stDownloadButton > button {
        border-radius: 14px;
        border: 1px solid rgba(73, 198, 255, 0.18);
        background: linear-gradient(180deg, #132338 0%, #0c1728 100%);
        color: #eaf2ff;
        font-weight: 700;
        box-shadow: 0 10px 20px rgba(0,0,0,0.22);
    }
    .stPopover button {
        border-radius: 14px !important;
        border: 1px solid rgba(73, 198, 255, 0.18) !important;
        background: linear-gradient(180deg, #132338 0%, #0c1728 100%) !important;
        color: #eaf2ff !important;
        font-weight: 700 !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.22) !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: rgba(73, 198, 255, 0.45);
        color: #ffffff;
    }
    .stPopover button:hover {
        border-color: rgba(73, 198, 255, 0.45) !important;
        color: #ffffff !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 999px;
        background: rgba(13, 22, 36, 0.95);
        color: #dce7f7;
        padding: 0.5rem 1rem;
        border: 1px solid rgba(110,170,255,0.10);
    }
    .stTabs [aria-selected="true"] {
        background: rgba(73, 198, 255, 0.12) !important;
        border-color: rgba(73, 198, 255, 0.30) !important;
        color: #ffffff !important;
    }
    .block-label {
        color: var(--muted);
        font-size: 0.88rem;
        margin-bottom: 0.6rem;
    }
    .stAlert {
        background: rgba(10, 16, 28, 0.88) !important;
        border: 1px solid var(--line) !important;
        color: #dce7f7 !important;
    }
    /* ── 输入控件：文字框 / 数字框 / 下拉框 ── */
    .stTextInput input,
    .stNumberInput input,
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] {
        background: #0c1728 !important;
        color: #eaf2ff !important;
        border-color: rgba(110,170,255,0.18) !important;
    }
    .stTextInput > div > div,
    .stNumberInput > div > div {
        background: #0c1728 !important;
        border: 1px solid rgba(110,170,255,0.18) !important;
        border-radius: 14px !important;
    }
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        background: linear-gradient(180deg, #0f1a2c 0%, #0b1422 100%) !important;
        border: 1px dashed rgba(110,170,255,0.22) !important;
        border-radius: 14px !important;
    }
    .stFileUploader [data-testid="stFileUploaderDropzone"]:hover {
        border-color: rgba(73,198,255,0.42) !important;
        background: linear-gradient(180deg, #12213a 0%, #0d1727 100%) !important;
    }
    .stFileUploader [data-testid="stFileUploaderDropzone"] * {
        color: #dce7f7 !important;
    }
    .stFileUploader section[data-testid="stFileUploaderDropzoneInstructions"] span,
    .stFileUploader small {
        color: #8ea3bd !important;
    }
    /* 下拉框已选值文字 */
    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] div {
        color: #eaf2ff !important;
    }
    /* 下拉弹出层（选项列表） */
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [role="listbox"] {
        background: #0e1e33 !important;
        border: 1px solid rgba(110,170,255,0.18) !important;
        border-radius: 10px !important;
    }
    [role="option"],
    [data-baseweb="menu"] li {
        background: transparent !important;
        color: #c8d8ea !important;
    }
    [role="option"]:hover,
    [data-baseweb="menu"] li:hover {
        background: rgba(73,198,255,0.10) !important;
        color: #ffffff !important;
    }
    [aria-selected="true"][role="option"] {
        background: rgba(73,198,255,0.15) !important;
        color: #7bc7ff !important;
    }
    /* 所有控件上方的 label */
    .stSelectbox label,
    .stTextInput label,
    .stNumberInput label,
    .stRadio label,
    .stCheckbox label,
    .stSlider label,
    .stMultiSelect label {
        color: #8ea3bd !important;
        font-size: 0.82rem !important;
    }
    /* radio 选项文字 */
    .stRadio [data-testid="stMarkdownContainer"] p,
    .stRadio div[role="radiogroup"] label {
        color: #c8d8ea !important;
    }
    /* expander 标题 */
    .streamlit-expanderHeader {
        color: #c8d8ea !important;
        background: rgba(10,16,28,0.6) !important;
    }
    /* metric 标签和值 */
    [data-testid="stMetricLabel"] {
        color: #8ea3bd !important;
    }
    [data-testid="stMetricValue"] {
        color: #eaf2ff !important;
    }
    [data-testid="stMetricDelta"] {
        color: #8ea3bd !important;
    }
    /* spinner 文字 */
    .stSpinner > div {
        color: #8ea3bd !important;
    }
    /* subheader */
    h3 {
        color: #dfe9f8 !important;
    }
    .stMarkdown, .stCaption, .stText {
        color: inherit;
    }
    /* ── 面板容器（st.container border=True 覆盖）── */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(10, 16, 28, 0.88) !important;
        border: 1px solid rgba(110, 170, 255, 0.14) !important;
        border-radius: 16px !important;
        box-shadow: 0 14px 34px rgba(0, 0, 0, 0.24) !important;
        padding: 0.2rem 0.4rem 0.6rem 0.4rem !important;
        margin-bottom: 1rem !important;
    }
    .news-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.85rem;
        margin-top: 0.35rem;
        margin-bottom: 0.3rem;
        align-items: stretch;
    }
    .news-card {
        background: linear-gradient(180deg, rgba(12, 19, 31, 0.98), rgba(8, 12, 20, 0.96));
        border: 1px solid rgba(110, 170, 255, 0.12);
        border-radius: 14px;
        padding: 0.95rem 1rem;
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.24);
        min-height: 140px;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .news-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.65rem;
        color: var(--muted);
        font-size: 0.78rem;
    }
    .news-source {
        color: #7bc7ff;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .news-time {
        color: var(--muted);
    }
    .news-title {
        font-size: 1rem;
        font-weight: 800;
        color: #f4f8ff;
        line-height: 1.35;
        margin-bottom: 0.5rem;
    }
    .news-body {
        color: #9fb2c8;
        font-size: 0.9rem;
        line-height: 1.5;
        flex: 1;
    }
    .news-empty {
        padding: 0.9rem 1rem;
        border: 1px dashed rgba(110, 170, 255, 0.18);
        border-radius: 14px;
        color: var(--muted);
        background: rgba(9, 14, 22, 0.72);
    }
    .suggestion-wrap {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
        margin-top: 0.35rem;
    }
    .suggestion-card {
        border: 1px solid rgba(110, 170, 255, 0.12);
        border-radius: 14px;
        background: linear-gradient(180deg, rgba(12, 19, 31, 0.96), rgba(8, 12, 20, 0.98));
        padding: 0.8rem 0.95rem 0.7rem 0.95rem;
        min-height: 92px;
    }
    .suggestion-market {
        font-size: 0.74rem;
        color: #7bc7ff;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
        font-weight: 700;
    }
    .suggestion-title {
        color: #edf4ff;
        font-weight: 800;
        line-height: 1.35;
        margin-bottom: 0.18rem;
        word-break: break-word;
    }
    .suggestion-symbol {
        color: #8ea3bd;
        font-size: 0.86rem;
        word-break: break-all;
    }
    @media (max-width: 900px) {
        .suggestion-wrap {
            grid-template-columns: 1fr;
        }
    }
    @media (max-width: 1100px) {
        .news-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    @media (max-width: 700px) {
        .news-grid {
            grid-template-columns: 1fr;
        }
        [data-testid="stPlotlyChart"] {
            touch-action: pinch-zoom !important;
        }
        [data-testid="stPlotlyChart"] > div,
        [data-testid="stPlotlyChart"] .js-plotly-plot,
        [data-testid="stPlotlyChart"] .plot-container,
        [data-testid="stPlotlyChart"] .svg-container {
            touch-action: pinch-zoom !important;
        }
        [data-testid="stPlotlyChart"] .draglayer,
        [data-testid="stPlotlyChart"] .nsewdrag,
        [data-testid="stPlotlyChart"] .zoombox,
        [data-testid="stPlotlyChart"] .plotly .main-svg {
            touch-action: none !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ─── 初始化 Tushare ───────────────────────────────────────────────
@st.cache_resource
def _create_tushare_pro():
    """缓存 pro 对象本身，而非初始化的副作用。"""
    token = getattr(config, "TUSHARE_TOKEN", "") or ""
    if not token:
        return None
    try:
        import tushare as ts
        pro = ts.pro_api(token=token)
        pro.trade_cal(exchange="SSE", start_date="20240101", end_date="20240102")
        return pro
    except Exception as e:
        print(f"[CN] Tushare 初始化失败: {e}")
        return None


# 每次 rerun 都把缓存的 pro 对象注入 cn_stocks 模块
_cached_pro = _create_tushare_pro()
cn_stocks._pro = _cached_pro
tushare_ok = _cached_pro is not None


# ─── 缓存数据获取（TTL=5分钟）────────────────────────────────────
def _disk_or_fetch(key: str, fetch_fn):
    """优先读今日磁盘缓存，无则请求并保存到磁盘。"""
    data = disk_cache.load(key)
    if data is not None:
        return data
    data = fetch_fn()
    if data is not None and not (hasattr(data, "empty") and data.empty):
        disk_cache.save(key, data)
    return data


def _rolling_cache_key(base_key: str, interval_seconds: int | None = None) -> str:
    seconds = max(int(interval_seconds or config.REFRESH_INTERVAL or 300), 30)
    bucket = int(time.time() // seconds)
    return f"{base_key}_{bucket}"


def get_us_watchlist() -> list[str]:
    return watchlist_store.get_watchlist("us", config.MY_US_WATCHLIST)


def get_cn_watchlist() -> list[str]:
    return watchlist_store.get_watchlist("cn", config.MY_CN_WATCHLIST)


def get_intl_futures_watchlist() -> list[str]:
    return watchlist_store.get_watchlist("intl_futures", [])


def get_cn_futures_watchlist() -> list[str]:
    return watchlist_store.get_watchlist("cn_futures", [])


def get_positions() -> list[dict]:
    return watchlist_store.get_positions()


WATCHLIST_DEFAULTS = {
    "us": config.MY_US_WATCHLIST,
    "cn": config.MY_CN_WATCHLIST,
    "intl_futures": [],
    "cn_futures": [],
}

MARKET_CONFIG = {
    "us": {"label": "美国股票", "asset_type": "us_stock", "symbol_col": "代码", "name_col": "名称"},
    "cn": {"label": "中国股票", "asset_type": "cn_stock", "symbol_col": "代码", "name_col": "名称"},
    "intl_futures": {"label": "国际期货", "asset_type": "intl_future", "symbol_col": "代码", "name_col": "品种"},
    "cn_futures": {"label": "国内期货", "asset_type": "cn_future", "symbol_col": "品种", "name_col": "品种"},
}
MARKET_CURRENCY = {
    "us": "USD",
    "cn": "CNY",
    "intl_futures": "USD",
    "cn_futures": "CNY",
}
US_SUGGESTION_LIBRARY = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "GOOGL": "Alphabet",
    "GOOG": "Alphabet",
    "META": "Meta",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "BABA": "Alibaba",
    "PDD": "PDD Holdings",
    "JD": "JD.com",
    "BIDU": "Baidu",
    "NFLX": "Netflix",
    "AMD": "AMD",
    "INTC": "Intel",
    "ORCL": "Oracle",
    "CRM": "Salesforce",
    "UBER": "Uber",
    "SHOP": "Shopify",
    "PYPL": "PayPal",
    "DIS": "Disney",
    "BRKB": "Berkshire Hathaway",
    "AVGO": "Broadcom",
    "QCOM": "Qualcomm",
    "MU": "Micron",
    "PLTR": "Palantir",
    "SNOW": "Snowflake",
    "SQ": "Block",
    "COIN": "Coinbase",
    "MSTR": "MicroStrategy",
    "SMCI": "Super Micro Computer",
    "ANET": "Arista Networks",
    "PANW": "Palo Alto Networks",
    "CRWD": "CrowdStrike",
    "ADBE": "Adobe",
    "NOW": "ServiceNow",
    "SAP": "SAP",
    "ASML": "ASML",
    "ARM": "Arm Holdings",
    "AMAT": "Applied Materials",
    "TSM": "Taiwan Semiconductor",
    "NIO": "NIO",
    "XPEV": "XPeng",
    "LI": "Li Auto",
    "BEKE": "KE Holdings",
    "BILI": "Bilibili",
    "BIDU": "Baidu",
    "GEV": "GE Vernova",
    "BE": "Bloom Energy",
    "QQQ": "Invesco QQQ Trust",
    "SPY": "SPDR S&P 500 ETF",
    "DIA": "SPDR Dow Jones Industrial Average ETF",
    "IWM": "iShares Russell 2000 ETF",
}

MARKET_LABEL_TO_KEY = {meta["label"]: key for key, meta in MARKET_CONFIG.items()}
MARKET_KEY_TO_LABEL = {key: meta["label"] for key, meta in MARKET_CONFIG.items()}

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_us_data(watchlist: tuple[str, ...], _version: str = "v3_user_watchlist"):
    watch_key = "_".join(watchlist) if watchlist else "empty"
    return _disk_or_fetch(
        _rolling_cache_key(f"us_data_{watch_key}"),
        lambda: us_stocks.get_quote(list(watchlist)),
    )

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_us_index():
    syms = ["^GSPC", "^IXIC", "^DJI"]
    return _disk_or_fetch(_rolling_cache_key("us_index"), lambda: us_stocks.get_quote(syms))

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_cn_index(_tushare_ready: bool = False):
    # _tushare_ready 作为 cache key 的一部分，确保 tushare 初始化后不复用旧缓存
    return _disk_or_fetch(_rolling_cache_key("cn_index"), cn_stocks.get_index_quote)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_cn_stocks(_tushare_ready: bool = False):
    return _disk_or_fetch(
        _rolling_cache_key("cn_stocks"),
        lambda: cn_stocks.get_stock_quote(config.MY_CN_WATCHLIST),
    )

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_cn_watchlist_data(watchlist: tuple[str, ...], _tushare_ready: bool = False):
    watch_key = "_".join(watchlist) if watchlist else "empty"
    return _disk_or_fetch(
        _rolling_cache_key(f"cn_watch_{watch_key}"),
        lambda: cn_stocks.get_stock_quote(list(watchlist)),
    )

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_futures():
    return _disk_or_fetch(
        _rolling_cache_key("intl_futures_v2"),
        lambda: futures.get_intl_futures_quote(config.MY_FUTURES_CATEGORIES),
    )

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_intl_futures_watchlist_data(watchlist: tuple[str, ...]):
    watch_key = "_".join(watchlist) if watchlist else "empty"

    def _fetch():
        df = futures.get_intl_futures_quote()
        if df is None or df.empty:
            return pd.DataFrame()
        if not watchlist:
            return df.iloc[0:0].copy()
        return df[df["代码"].isin(list(watchlist))].reset_index(drop=True)

    return _disk_or_fetch(_rolling_cache_key(f"intl_fut_watch_v2_{watch_key}"), _fetch)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_cn_futures():
    return _disk_or_fetch(_rolling_cache_key("cn_futures"), futures.get_cn_futures_quote)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_cn_futures_watchlist_data(watchlist: tuple[str, ...]):
    watch_key = "_".join(watchlist) if watchlist else "empty"

    def _fetch():
        df = futures.get_cn_futures_quote()
        if df is None or df.empty:
            return pd.DataFrame()
        if not watchlist:
            return df.iloc[0:0].copy()
        return df[df["品种"].isin(list(watchlist))].reset_index(drop=True)

    return _disk_or_fetch(_rolling_cache_key(f"cn_fut_watch_{watch_key}"), _fetch)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_sector_performance():
    return _disk_or_fetch(_rolling_cache_key("sector_perf"), us_stocks.get_sector_performance)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_sector_constituents():
    return _disk_or_fetch(
        _rolling_cache_key("sector_constituents"),
        us_stocks.get_sector_constituent_performance,
    )

@st.cache_data(ttl=3600)
def load_earnings_calendar(watchlist: tuple[str, ...]):
    return us_stocks.get_earnings_calendar(list(watchlist))

@st.cache_data(ttl=3600)
def get_sparkline_prices(symbol: str, days: int = 30) -> list:
    try:
        import yfinance as yf
        hist = yf.Ticker(symbol).history(period=f"{days}d", interval="1d")
        if hist.empty:
            return []
        return hist["Close"].dropna().tolist()
    except Exception:
        return []


@st.cache_data(ttl=3600)
def load_next_us_earnings_date(symbol: str) -> str:
    try:
        import yfinance as yf

        cal = yf.Ticker(symbol).calendar
        if cal and isinstance(cal, dict):
            dates = cal.get("Earnings Date") or []
            if dates:
                return pd.Timestamp(dates[0]).strftime("%Y-%m-%d")
    except Exception:
        pass
    return ""

# 品种名 → (product_prefix, tushare_exchange)
CN_FUTURES_TS_CODE = {
    "螺纹钢":    ("RB",  "SHFE"),
    "铁矿石":    ("I",   "DCE"),
    "热轧卷板":  ("HC",  "SHFE"),
    "焦炭":      ("J",   "DCE"),
    "焦煤":      ("JM",  "DCE"),
    "沪铜":      ("CU",  "SHFE"),
    "沪铝":      ("AL",  "SHFE"),
    "沪锌":      ("ZN",  "SHFE"),
    "沪镍":      ("NI",  "SHFE"),
    "沪锡":      ("SN",  "SHFE"),
    "沪金":      ("AU",  "SHFE"),
    "沪银":      ("AG",  "SHFE"),
    "原油":      ("SC",  "INE"),
    "PTA":       ("TA",  "CZCE"),
    "甲醇":      ("MA",  "CZCE"),
    "液化石油气": ("PG",  "DCE"),
    "豆粕":      ("M",   "DCE"),
    "豆油":      ("Y",   "DCE"),
    "棕榈油":    ("P",   "DCE"),
    "玉米":      ("C",   "DCE"),
    "玉米淀粉":  ("CS",  "DCE"),
    "沪深300":   ("IF",  "CFFEX"),
    "中证500":   ("IC",  "CFFEX"),
    "上证50":    ("IH",  "CFFEX"),
    "中证1000":  ("IM",  "CFFEX"),
}

@st.cache_data(ttl=3600)
def _get_main_fut_code(product: str, exchange: str) -> str:
    """查当前主力合约 ts_code（按成交量最大）"""
    try:
        import tushare as ts
        from datetime import timedelta
        token = getattr(config, "TUSHARE_TOKEN", "") or ""
        if not token:
            return ""
        pro = ts.pro_api(token=token)
        # 往前找最近有交易的日期（最多回溯 7 天）
        for offset in range(7):
            trade_date = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
            df = pro.fut_daily(trade_date=trade_date, exchange=exchange,
                               fields="ts_code,vol")
            if df is not None and not df.empty:
                break
        else:
            return ""
        prod_df = df[df["ts_code"].str.upper().str.startswith(product.upper())]
        if prod_df.empty:
            return ""
        return prod_df.loc[prod_df["vol"].idxmax(), "ts_code"]
    except Exception as e:
        print(f"[Sparkline] 主力合约查询失败 {product}.{exchange}: {e}")
        return ""

@st.cache_data(ttl=3600)
def get_sparkline_prices_ts(product: str, exchange: str, days: int = 30) -> list:
    """用 Tushare 获取国内期货主力合约历史收盘价"""
    try:
        import tushare as ts
        from datetime import timedelta
        token = getattr(config, "TUSHARE_TOKEN", "") or ""
        if not token:
            return []
        main_code = _get_main_fut_code(product, exchange)
        if not main_code:
            print(f"[Sparkline] 未找到主力合约: {product}.{exchange}")
            return []
        pro = ts.pro_api(token=token)
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
        df = pro.fut_daily(ts_code=main_code, start_date=start, end_date=end,
                           fields="trade_date,close")
        if df is None or df.empty:
            return []
        df = df.sort_values("trade_date")
        return df["close"].dropna().tolist()[-days:]
    except Exception as e:
        print(f"[Sparkline] Tushare 期货历史失败 {product}.{exchange}: {e}")
        return []

@st.cache_data(ttl=3600)
def load_cn_history(ts_code: str) -> "pd.DataFrame":
    return cn_stocks.get_history(ts_code)

@st.cache_data(ttl=3600)
def load_cn_futures_history(product: str) -> "pd.DataFrame":
    try:
        import tushare as ts
        from datetime import timedelta

        meta = CN_FUTURES_TS_CODE.get(product)
        token = getattr(config, "TUSHARE_TOKEN", "") or ""
        if not meta or not token:
            return pd.DataFrame()

        prod, exchange = meta
        main_code = _get_main_fut_code(prod, exchange)
        if not main_code:
            return pd.DataFrame()

        pro = ts.pro_api(token=token)
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=240)).strftime("%Y%m%d")
        df = pro.fut_daily(
            ts_code=main_code,
            start_date=start,
            end_date=end,
            fields="trade_date,open,high,low,close,vol",
        )
        if df is None or df.empty:
            return pd.DataFrame()
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date").set_index("trade_date")
        df = df[["open", "high", "low", "close", "vol"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        return df.dropna()
    except Exception as e:
        print(f"[CN Futures] 历史数据获取失败 {product}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_usdcny_rate() -> float:
    try:
        import yfinance as yf

        hist = yf.Ticker("USDCNY=X").history(period="5d", interval="1d")
        close = pd.to_numeric(hist.get("Close"), errors="coerce").dropna()
        if not close.empty and float(close.iloc[-1]) > 0:
            return float(close.iloc[-1])
    except Exception as e:
        print(f"[FX] USD/CNY 获取失败: {e}")
    return 7.2


def convert_amount_to_usd(amount, market_key: str):
    numeric = pd.to_numeric(amount, errors="coerce")
    if pd.isna(numeric):
        return None
    if get_market_currency(market_key) == "CNY":
        rate = load_usdcny_rate()
        return float(numeric) / rate if rate else float(numeric)
    return float(numeric)


def get_kline_cache_key(hist: "pd.DataFrame", symbol: str = "", asset_type: str = "") -> str:
    """用资产身份 + 最后一根 K 线作为 AI 缓存失效依据。"""
    if hist is None or hist.empty:
        return f"{asset_type}|{symbol}|empty"
    last_idx = hist.index[-1]
    last = hist.iloc[-1]
    idx_str = pd.Timestamp(last_idx).isoformat() if not pd.isna(last_idx) else "na"
    return "|".join([
        asset_type,
        symbol,
        idx_str,
        f"{float(last.get('open', 0)):.6f}",
        f"{float(last.get('high', 0)):.6f}",
        f"{float(last.get('low', 0)):.6f}",
        f"{float(last.get('close', 0)):.6f}",
        f"{float(last.get('volume', 0)):.2f}",
    ])


@st.cache_data(ttl=None)
def get_ai_market_asset_analysis(symbol: str, display_name: str, asset_type: str, kline_key: str, _hist: "pd.DataFrame") -> str:
    return ai_brief.analyze_market_asset(symbol, display_name, asset_type, _hist)


@st.cache_data(ttl=None)
def get_ai_stock_detail(symbol: str, display_name: str, kline_key: str, _hist: "pd.DataFrame") -> str:
    return ai_brief.analyze_stock_detail(symbol, display_name, _hist)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_hsgt_history(days: int = 30) -> "pd.DataFrame":
    return cn_stocks.get_hsgt_flow_history(days=days)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_ggt_net_buy_latest() -> dict:
    return cn_stocks.get_ggt_net_buy_latest()

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_ggt_net_buy_history(days: int = 30) -> "pd.DataFrame":
    return cn_stocks.get_ggt_net_buy_history(days=days)


def open_asset_detail(symbol: str, name: str, asset_type: str):
    st.session_state["selected_asset"] = {
        "symbol": symbol,
        "name": name,
        "type": asset_type,
    }
    st.session_state["detail_request_id"] = st.session_state.get("detail_request_id", 0) + 1


def get_market_key_from_label(label: str) -> str:
    return MARKET_LABEL_TO_KEY.get(label, "us")


def get_market_asset_type(market_key: str) -> str:
    return MARKET_CONFIG.get(market_key, {}).get("asset_type", "")


def get_market_currency(market_key: str) -> str:
    return MARKET_CURRENCY.get(market_key, "USD")


def get_market_watchlists() -> dict[str, list[str]]:
    return watchlist_store.get_all_watchlists(WATCHLIST_DEFAULTS)


def parse_symbol_input(raw_text: str, uppercase: bool = True) -> list[str]:
    normalized = (
        str(raw_text or "")
        .replace("，", ",")
        .replace("、", ",")
        .replace("\n", ",")
        .replace(" ", ",")
    )
    symbols = []
    for item in normalized.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        symbols.append(cleaned.upper() if uppercase else cleaned)
    return symbols


def normalize_symbols_for_market(symbols: list[str], market_key: str) -> list[str]:
    normalized = []
    seen = set()
    for raw_symbol in symbols or []:
        symbol = str(raw_symbol or "").strip()
        if not symbol:
            continue
        if market_key == "cn":
            upper_symbol = symbol.upper()
            if "." not in upper_symbol and upper_symbol.isdigit() and len(upper_symbol) == 6:
                suffix = ".SH" if upper_symbol.startswith(("5", "6", "9")) else ".SZ"
                symbol = f"{upper_symbol}{suffix}"
            else:
                symbol = upper_symbol
        elif market_key != "cn_futures":
            symbol = symbol.upper()
        if symbol in seen:
            continue
        seen.add(symbol)
        normalized.append(symbol)
    return normalized


def _normalize_search_text(text: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9\u4e00-\u9fff]+", "", str(text or "").upper())
    if cleaned.endswith("S") and len(cleaned) > 3:
        cleaned = cleaned[:-1]
    return cleaned


def _lookup_catalog_name(market_key: str, symbol: str) -> str:
    normalized_symbol = str(symbol or "").strip().upper()
    raw_symbol = normalized_symbol.split(".")[0] if market_key == "cn" else normalized_symbol
    for item in build_asset_suggestion_catalog().get(market_key, []):
        item_symbol = str(item.get("symbol", "")).strip().upper()
        item_raw_symbol = str(item.get("raw_symbol", "")).strip().upper()
        if normalized_symbol and (item_symbol == normalized_symbol or item_raw_symbol == raw_symbol):
            return str(item.get("name", "")).strip()
    return ""


def get_canonical_asset_name(
    market_key: str,
    symbol: str,
    fallback_name: str = "",
    quote_name: str = "",
) -> str:
    normalized_symbol = str(symbol or "").strip().upper()
    for candidate in [
        str(quote_name or "").strip(),
        us_stocks.INDEX_NAMES.get(normalized_symbol, "") if market_key == "us" else "",
        us_stocks.STOCK_DISPLAY_NAMES.get(normalized_symbol, "") if market_key == "us" else "",
        US_SUGGESTION_LIBRARY.get(normalized_symbol, "") if market_key == "us" else "",
        _lookup_catalog_name(market_key, normalized_symbol),
        str(fallback_name or "").strip(),
        normalized_symbol,
    ]:
        if candidate:
            return candidate
    return normalized_symbol


@st.cache_data(ttl=3600 * 24)
def load_cn_stock_basic_catalog() -> list[dict]:
    try:
        pro = _cached_pro or getattr(cn_stocks, "_pro", None)
        if pro is None:
            return []
        df = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name",
        )
        if df is None or df.empty:
            return []
        records = []
        for _, row in df.iterrows():
            ts_code = str(row.get("ts_code", "")).strip().upper()
            symbol = str(row.get("symbol", "")).strip().upper()
            name = str(row.get("name", "")).strip()
            if not ts_code:
                continue
            records.append(
                {
                    "symbol": ts_code,
                    "raw_symbol": symbol or ts_code.split(".")[0],
                    "name": name or ts_code,
                    "market": "中国股票",
                    "market_key": "cn",
                }
            )
        return records
    except Exception as e:
        print(f"[Suggest] A股基础清单加载失败: {e}")
        return []


@st.cache_data(ttl=3600)
def build_asset_suggestion_catalog() -> dict[str, list[dict]]:
    catalog: dict[str, list[dict]] = {
        "us": [],
        "cn": [],
        "intl_futures": [],
        "cn_futures": [],
    }

    us_seen = set()
    us_symbols = []
    for group_symbols in us_stocks.DEFAULT_US_STOCKS.values():
        us_symbols.extend(group_symbols)
    us_symbols.extend(us_stocks.STOCK_DISPLAY_NAMES.keys())
    us_symbols.extend(US_SUGGESTION_LIBRARY.keys())
    us_symbols.extend(config.MY_US_WATCHLIST)
    for symbol in us_symbols:
        sym = str(symbol or "").strip().upper()
        if not sym or sym in us_seen:
            continue
        us_seen.add(sym)
        name = (
            us_stocks.INDEX_NAMES.get(sym)
            or us_stocks.STOCK_DISPLAY_NAMES.get(sym)
            or US_SUGGESTION_LIBRARY.get(sym)
            or sym
        )
        catalog["us"].append({"symbol": sym, "raw_symbol": sym, "name": name, "market": "美国股票", "market_key": "us"})

    cn_seen = set()
    cn_catalog = load_cn_stock_basic_catalog()
    if cn_catalog:
        for item in cn_catalog:
            sym = str(item.get("symbol", "")).strip().upper()
            if not sym or sym in cn_seen:
                continue
            cn_seen.add(sym)
            catalog["cn"].append(item)
    else:
        cn_items = []
        for group in cn_stocks.DEFAULT_CN_STOCKS.values():
            cn_items.extend(group)
        for symbol in config.MY_CN_WATCHLIST:
            cn_items.append((symbol, symbol))
        for symbol, name in cn_items:
            sym = str(symbol or "").strip().upper()
            if not sym or sym in cn_seen:
                continue
            cn_seen.add(sym)
            catalog["cn"].append(
                {
                    "symbol": sym,
                    "raw_symbol": sym.split(".")[0],
                    "name": str(name or sym).strip(),
                    "market": "中国股票",
                    "market_key": "cn",
                }
            )

    intl_seen = set()
    for category, items in futures.INTL_FUTURES.items():
        for symbol, name in items:
            sym = str(symbol or "").strip().upper()
            if not sym or sym in intl_seen:
                continue
            intl_seen.add(sym)
            catalog["intl_futures"].append({"symbol": sym, "name": str(name or sym).strip(), "market": f"国际期货 · {category}", "market_key": "intl_futures"})

    cn_fut_seen = set()
    for name, (product_prefix, exchange) in CN_FUTURES_TS_CODE.items():
        sym = str(name or "").strip()
        if not sym or sym in cn_fut_seen:
            continue
        cn_fut_seen.add(sym)
        catalog["cn_futures"].append({"symbol": sym, "name": sym, "market": f"国内期货 · {exchange}", "market_key": "cn_futures"})

    return catalog


def search_asset_suggestions(query: str, market_key: str, limit: int = 8) -> list[dict]:
    text = str(query or "").strip()
    if not text:
        return []
    normalized_query = text.upper()
    if market_key == "cn":
        normalized_candidates = normalize_symbols_for_market([normalized_query], "cn")
        normalized_query = normalized_candidates[0] if normalized_candidates else normalized_query
    folded_query = _normalize_search_text(normalized_query)

    candidates = build_asset_suggestion_catalog().get(market_key, [])
    scored = []
    for item in candidates:
        symbol = str(item.get("symbol", "")).strip()
        raw_symbol = str(item.get("raw_symbol", "")).strip()
        name = str(item.get("name", "")).strip()
        symbol_upper = symbol.upper()
        raw_symbol_upper = raw_symbol.upper()
        name_upper = name.upper()
        folded_symbol = _normalize_search_text(symbol_upper)
        folded_raw_symbol = _normalize_search_text(raw_symbol_upper)
        folded_name = _normalize_search_text(name_upper)
        score = None
        if symbol_upper == normalized_query or raw_symbol_upper == normalized_query or name_upper == normalized_query:
            score = 0
        elif folded_query and (folded_symbol == folded_query or folded_raw_symbol == folded_query or folded_name == folded_query):
            score = 0
        elif (
            symbol_upper.startswith(normalized_query)
            or raw_symbol_upper.startswith(normalized_query)
            or name_upper.startswith(normalized_query)
        ):
            score = 1
        elif folded_query and (
            folded_symbol.startswith(folded_query)
            or folded_raw_symbol.startswith(folded_query)
            or folded_name.startswith(folded_query)
        ):
            score = 1
        elif normalized_query in symbol_upper or normalized_query in raw_symbol_upper or normalized_query in name_upper:
            score = 2
        elif folded_query and (
            folded_query in folded_symbol
            or folded_query in folded_raw_symbol
            or folded_query in folded_name
        ):
            score = 2
        if score is not None:
            scored.append((score, len(symbol), name, item))
    scored.sort(key=lambda row: (row[0], row[1], row[2]))
    return [item for _, _, _, item in scored[:limit]]


def search_all_asset_suggestions(query: str, limit: int = 10) -> list[dict]:
    text = str(query or "").strip()
    if not text:
        return []
    all_items = []
    for market_key in ["us", "cn", "intl_futures", "cn_futures"]:
        all_items.extend(search_asset_suggestions(text, market_key, limit=limit))
    deduped = []
    seen = set()
    for item in all_items:
        token = (str(item.get("market_key", "")), str(item.get("symbol", "")))
        if token in seen:
            continue
        seen.add(token)
        deduped.append(item)
    return deduped[:limit]


def infer_market_for_manual_watch(query: str) -> tuple[str | None, list[str]]:
    text = str(query or "").strip()
    if not text:
        return None, []
    parsed = parse_symbol_input(text, uppercase=True)
    suggestions = search_all_asset_suggestions(text, limit=6)
    exact_matches = [
        item for item in suggestions
        if _normalize_search_text(item.get("symbol", "")) == _normalize_search_text(text)
        or _normalize_search_text(item.get("raw_symbol", "")) == _normalize_search_text(text)
        or _normalize_search_text(item.get("name", "")) == _normalize_search_text(text)
    ]
    if len(exact_matches) == 1:
        item = exact_matches[0]
        return str(item.get("market_key", "")).strip(), [str(item.get("symbol", "")).strip()]

    if len(parsed) == 1:
        raw = parsed[0]
        upper = raw.upper()
        if upper.endswith("=F"):
            return "intl_futures", [upper]
        if "." in upper and upper.endswith((".SH", ".SZ")):
            return "cn", normalize_symbols_for_market([upper], "cn")
        if upper.isdigit() and len(upper) == 6:
            return "cn", normalize_symbols_for_market([upper], "cn")
        if raw in CN_FUTURES_TS_CODE:
            return "cn_futures", [raw]
        if re.fullmatch(r"[A-Z.\-]{1,10}", upper):
            return "us", [upper]
    return None, []


def infer_asset_for_manual_position(query: str) -> dict | None:
    text = str(query or "").strip()
    if not text:
        return None

    suggestions = search_all_asset_suggestions(text, limit=6)
    normalized_text = _normalize_search_text(text)
    exact_matches = [
        item for item in suggestions
        if _normalize_search_text(item.get("symbol", "")) == normalized_text
        or _normalize_search_text(item.get("raw_symbol", "")) == normalized_text
        or _normalize_search_text(item.get("name", "")) == normalized_text
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]

    market_key, symbols = infer_market_for_manual_watch(text)
    if not market_key or len(symbols) != 1:
        return None

    inferred_symbol = str(symbols[0]).strip()
    inferred_matches = search_asset_suggestions(inferred_symbol, market_key, limit=4)
    inferred_exact = [
        item for item in inferred_matches
        if _normalize_search_text(item.get("symbol", "")) == _normalize_search_text(inferred_symbol)
        or _normalize_search_text(item.get("raw_symbol", "")) == _normalize_search_text(inferred_symbol)
    ]
    if inferred_exact:
        return inferred_exact[0]

    return {
        "market_key": market_key,
        "market": MARKET_KEY_TO_LABEL.get(market_key, market_key),
        "symbol": inferred_symbol,
        "raw_symbol": inferred_symbol.split(".")[0] if market_key == "cn" else inferred_symbol,
        "name": inferred_symbol,
    }


def _find_existing_position_index(market_label: str, symbol: str) -> int | None:
    normalized_market = str(market_label or "").strip()
    normalized_symbol = str(symbol or "").strip().upper()
    for idx, item in enumerate(get_positions()):
        if (
            str(item.get("market", "")).strip() == normalized_market
            and str(item.get("symbol", "")).strip().upper() == normalized_symbol
        ):
            return idx
    return None


def _save_manual_position_entry(asset_item: dict, quantity: float, cost: float, merge_with_existing: bool) -> None:
    market_key = str(asset_item.get("market_key", "")).strip()
    symbol = str(asset_item.get("symbol", "")).strip()
    market_label = MARKET_KEY_TO_LABEL.get(market_key, str(asset_item.get("market", "")).strip() or market_key)
    asset_name = get_canonical_asset_name(
        market_key,
        symbol,
        fallback_name=str(asset_item.get("name", symbol)).strip() or symbol,
    )
    existing_index = _find_existing_position_index(market_label, symbol)

    if merge_with_existing and existing_index is not None:
        existing = get_positions()[existing_index]
        old_qty = float(existing.get("quantity", 0) or 0)
        old_cost = float(existing.get("cost", 0) or 0)
        new_qty = float(quantity or 0)
        total_qty = old_qty + new_qty
        if new_qty > 0 and old_qty > 0 and total_qty > 0:
            merged_cost = ((old_qty * old_cost) + (new_qty * float(cost or 0))) / total_qty
        elif total_qty > 0:
            merged_cost = old_cost
        elif total_qty < 0:
            merged_cost = float(cost or 0) if float(cost or 0) > 0 else old_cost
        else:
            merged_cost = 0.0
        watchlist_store.upsert_position(
            {
                "market": market_label,
                "symbol": symbol,
                "name": asset_name,
                "quantity": total_qty,
                "cost": merged_cost,
                "note": str(existing.get("note", "")).strip(),
            },
            index=existing_index,
        )
        st.session_state["manual_position_add_feedback"] = (
            f"已合并持仓：{asset_name} ({symbol})，当前数量 {total_qty:g}，持仓成本 {merged_cost:g}"
        )
    else:
        watchlist_store.upsert_position(
            {
                "market": market_label,
                "symbol": symbol,
                "name": asset_name,
                "quantity": float(quantity or 0),
                "cost": float(cost or 0),
                "note": "",
            }
        )
        st.session_state["manual_position_add_feedback"] = (
            f"已添加持仓：{asset_name} ({symbol})，数量 {float(quantity or 0):g}，成本 {float(cost or 0):g}"
        )

    st.session_state["manual_position_pending_merge"] = None
    st.session_state["manual_position_symbols"] = ""
    st.session_state["manual_position_symbols_keyup"] = ""
    st.cache_data.clear()
    st.rerun()


def add_manual_position_entry(asset_item: dict, quantity: float, cost: float) -> None:
    market_key = str(asset_item.get("market_key", "")).strip()
    symbol = str(asset_item.get("symbol", "")).strip()
    if not market_key or not symbol:
        st.warning("请先选择有效的持仓资产。")
        return
    qty = float(quantity or 0)
    unit_cost = float(cost or 0)
    if qty == 0:
        st.warning("数量不能为 0，没有仓位不能添加。")
        return

    market_label = MARKET_KEY_TO_LABEL.get(market_key, str(asset_item.get("market", "")).strip() or market_key)
    existing_index = _find_existing_position_index(market_label, symbol)
    if existing_index is not None:
        st.session_state["manual_position_pending_merge"] = {
            "asset_item": asset_item,
            "quantity": qty,
            "cost": unit_cost,
            "existing_index": existing_index,
        }
        return

    _save_manual_position_entry(asset_item, qty, unit_cost, merge_with_existing=False)


def get_market_data(market_key: str, symbols: list[str]) -> pd.DataFrame:
    symbols = [str(item).strip() for item in symbols if str(item).strip()]
    if market_key == "us":
        return load_us_data(tuple([item.upper() for item in symbols]))
    if market_key == "cn":
        return load_cn_watchlist_data(tuple(symbols), _tushare_ready=tushare_ok)
    if market_key == "intl_futures":
        return load_intl_futures_watchlist_data(tuple(symbols))
    if market_key == "cn_futures":
        return load_cn_futures_watchlist_data(tuple(symbols))
    return pd.DataFrame()


def build_watchlist_market_frame(market_key: str, symbols: list[str]) -> pd.DataFrame:
    df = get_market_data(market_key, symbols)
    market_label = MARKET_KEY_TO_LABEL.get(market_key, market_key)
    name_col = MARKET_CONFIG[market_key]["name_col"]
    symbol_col = MARKET_CONFIG[market_key]["symbol_col"]
    if df is None or df.empty:
        fallback_rows = []
        for symbol in symbols:
            canonical_name = get_canonical_asset_name(market_key, symbol, fallback_name=symbol)
            fallback_rows.append(
                {
                    "市场": market_label,
                    "资产名称": canonical_name,
                    "资产代码": symbol,
                    "现价": "",
                    "涨跌额": "",
                    "涨跌幅%": "",
                    "更新时间": "",
                    "asset_symbol": symbol,
                    "asset_name": canonical_name,
                    "asset_type": get_market_asset_type(market_key),
                }
            )
        return pd.DataFrame(fallback_rows)

    out = df.copy()
    order_map = {str(symbol).strip().upper(): idx for idx, symbol in enumerate(symbols)}
    out["_display_order"] = out[symbol_col].astype(str).str.strip().str.upper().map(order_map).fillna(len(symbols))
    out = out.sort_values("_display_order").drop(columns="_display_order").reset_index(drop=True)
    out["市场"] = market_label
    out["资产代码"] = out[symbol_col]
    out["资产名称"] = out.apply(
        lambda row: get_canonical_asset_name(
            market_key,
            str(row.get(symbol_col, "")),
            fallback_name=str(row.get(name_col, "")),
            quote_name=str(row.get(name_col, "")),
        ),
        axis=1,
    )
    out["asset_symbol"] = out[symbol_col]
    out["asset_name"] = out["资产名称"]
    out["asset_type"] = get_market_asset_type(market_key)
    return out


def build_total_watchlist_frame(watchlists: dict[str, list[str]]) -> pd.DataFrame:
    frames = []
    for market_key in ["us", "cn", "intl_futures", "cn_futures"]:
        symbols = watchlists.get(market_key, [])
        if not symbols:
            continue
        df = build_watchlist_market_frame(market_key, symbols)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _format_volume_value(value) -> str:
    if value is None or value == "":
        return ""
    try:
        numeric = float(value)
    except Exception:
        return str(value)
    if abs(numeric) >= 1_000_000_000:
        return f"{numeric / 1_000_000_000:.2f}B"
    if abs(numeric) >= 1_000_000:
        return f"{numeric / 1_000_000:.2f}M"
    if abs(numeric) >= 10_000:
        return f"{numeric / 10_000:.2f}万"
    return f"{numeric:.0f}"


def _compute_rsi(hist: pd.DataFrame, period: int = 14) -> float | None:
    if hist is None or hist.empty or "close" not in hist.columns or len(hist) < period + 1:
        return None
    close = pd.to_numeric(hist["close"], errors="coerce").dropna()
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    if pd.isna(last_gain) or pd.isna(last_loss):
        return None
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return 100 - (100 / (1 + rs))


def _calc_return(current: float, base: float | None) -> float | None:
    if base in (None, 0) or pd.isna(base):
        return None
    return (current / base - 1) * 100


def _compute_period_performance(hist: pd.DataFrame) -> dict:
    if hist is None or hist.empty or "close" not in hist.columns:
        return {"today": None, "week": None, "month": None, "ytd": None, "year": None}
    close = pd.to_numeric(hist["close"], errors="coerce").dropna()
    if len(close) < 2:
        return {"today": None, "week": None, "month": None, "ytd": None, "year": None}
    current = float(close.iloc[-1])
    values = {
        "today": _calc_return(current, float(close.iloc[-2])) if len(close) >= 2 else None,
        "week": _calc_return(current, float(close.iloc[-6])) if len(close) >= 6 else None,
        "month": _calc_return(current, float(close.iloc[-22])) if len(close) >= 22 else None,
        "year": _calc_return(current, float(close.iloc[-253])) if len(close) >= 253 else _calc_return(current, float(close.iloc[0])),
    }
    current_year = datetime.now().year
    index_series = pd.DatetimeIndex(close.index)
    try:
        if index_series.tz is not None:
            ytd_start = pd.Timestamp(f"{current_year}-01-01", tz=index_series.tz)
        else:
            ytd_start = pd.Timestamp(f"{current_year}-01-01")
    except Exception:
        ytd_start = pd.Timestamp(f"{current_year}-01-01")
    ytd_series = close[index_series >= ytd_start]
    values["ytd"] = _calc_return(current, float(ytd_series.iloc[0])) if len(ytd_series) >= 1 else None
    return values


def get_position_history(asset_type: str, symbol: str) -> pd.DataFrame:
    if asset_type == "us_stock":
        return load_us_history(symbol, "1y")
    if asset_type in ("cn_stock", "cn_index"):
        return load_cn_history(symbol)
    if asset_type == "intl_future":
        return load_futures_history(symbol, "1y")
    if asset_type == "cn_future":
        return load_cn_futures_history(symbol)
    return pd.DataFrame()


def get_position_quote_row(position: dict) -> dict:
    market_key = get_market_key_from_label(position.get("market", ""))
    symbol = str(position.get("symbol", "")).strip()
    if not symbol:
        return {}
    df = get_market_data(market_key, [symbol])
    if df is None or df.empty:
        return {}
    config_meta = MARKET_CONFIG[market_key]
    symbol_col = config_meta["symbol_col"]
    name_col = config_meta["name_col"]
    row = df.iloc[0].to_dict()
    row["asset_symbol"] = row.get(symbol_col, symbol)
    row["asset_name"] = get_canonical_asset_name(
        market_key,
        str(row.get(symbol_col, symbol)),
        fallback_name=str(position.get("name", symbol)),
        quote_name=str(row.get(name_col, "")),
    )
    row["asset_type"] = config_meta["asset_type"]
    return row


POSITION_FRAME_COLUMNS = [
    "index", "市场", "代码", "名称", "持仓数量", "持仓成本", "现价", "涨跌", "涨跌%",
    "成交量", "RSI", "持仓市值", "浮盈亏", "浮盈亏%", "计价货币",
    "持仓成本USD", "持仓市值USD", "浮盈亏USD",
    "今日", "一周", "一个月", "今年至今", "全年", "下一财报",
    "asset_symbol", "asset_name", "asset_type",
]


def build_positions_frame(positions: list[dict]) -> pd.DataFrame:
    rows = []
    for idx, position in enumerate(positions):
        quote_row = get_position_quote_row(position)
        current_price = pd.to_numeric(quote_row.get("现价"), errors="coerce")
        quantity = pd.to_numeric(position.get("quantity"), errors="coerce")
        cost = pd.to_numeric(position.get("cost"), errors="coerce")
        if pd.isna(quantity):
            quantity = 0.0
        if pd.isna(cost):
            cost = 0.0
        market_label = position.get("market", "")
        symbol = position.get("symbol", "")
        market_key = get_market_key_from_label(market_label)
        name = get_canonical_asset_name(
            market_key,
            symbol,
            fallback_name=str(position.get("name", "")),
            quote_name=str(quote_row.get("asset_name", "")),
        )
        asset_type = get_market_asset_type(market_key)
        quote_currency = get_market_currency(market_key)
        hist = get_position_history(asset_type, symbol)
        perf = _compute_period_performance(hist)
        rsi = _compute_rsi(hist)
        cost_amount = float(quantity) * float(cost)
        current_amount = float(quantity) * float(current_price) if pd.notna(current_price) else None
        pnl_amount = current_amount - cost_amount if current_amount is not None else None
        pnl_pct = (pnl_amount / cost_amount * 100) if cost_amount and pnl_amount is not None else None
        cost_amount_usd = convert_amount_to_usd(cost_amount, market_key)
        current_amount_usd = convert_amount_to_usd(current_amount, market_key) if current_amount is not None else None
        pnl_amount_usd = convert_amount_to_usd(pnl_amount, market_key) if pnl_amount is not None else None
        volume_value = (
            quote_row.get("成交量")
            if "成交量" in quote_row
            else quote_row.get("成交量(亿)")
            if "成交量(亿)" in quote_row
            else quote_row.get("成交量(万手)")
        )
        next_earnings = load_next_us_earnings_date(symbol) if asset_type == "us_stock" else ""
        rows.append(
            {
                "index": idx,
                "市场": market_label,
                "代码": symbol,
                "名称": name,
                "持仓数量": float(quantity),
                "持仓成本": float(cost),
                "现价": round(float(current_price), 4) if pd.notna(current_price) else "",
                "涨跌": quote_row.get("涨跌额", ""),
                "涨跌%": quote_row.get("涨跌幅%", quote_row.get("涨跌幅", "")),
                "成交量": _format_volume_value(volume_value),
                "RSI": round(rsi, 2) if rsi is not None else "",
                "持仓市值": round(current_amount, 2) if current_amount is not None else "",
                "浮盈亏": round(pnl_amount, 2) if pnl_amount is not None else "",
                "浮盈亏%": round(pnl_pct, 2) if pnl_pct is not None else "",
                "计价货币": quote_currency,
                "持仓成本USD": round(cost_amount_usd, 2) if cost_amount_usd is not None else "",
                "持仓市值USD": round(current_amount_usd, 2) if current_amount_usd is not None else "",
                "浮盈亏USD": round(pnl_amount_usd, 2) if pnl_amount_usd is not None else "",
                "今日": round(perf["today"], 2) if perf["today"] is not None else "",
                "一周": round(perf["week"], 2) if perf["week"] is not None else "",
                "一个月": round(perf["month"], 2) if perf["month"] is not None else "",
                "今年至今": round(perf["ytd"], 2) if perf["ytd"] is not None else "",
                "全年": round(perf["year"], 2) if perf["year"] is not None else "",
                "下一财报": next_earnings,
                "asset_symbol": symbol,
                "asset_name": name,
                "asset_type": asset_type,
            }
        )
    return pd.DataFrame(rows, columns=POSITION_FRAME_COLUMNS)


def build_watchlist_monitor_frame(watchlists: dict[str, list[str]]) -> pd.DataFrame:
    monitor_order = watchlist_store.get_watchlist_monitor_order()
    monitor_order_map = {key: idx for idx, key in enumerate(monitor_order)}
    rows = []
    for market_key in ["us", "cn", "intl_futures", "cn_futures"]:
        symbols = watchlists.get(market_key, [])
        market_df = build_watchlist_market_frame(market_key, symbols)
        if market_df is None or market_df.empty:
            continue
        for source_index, (_, row) in enumerate(market_df.iterrows()):
            asset_type = str(row.get("asset_type", ""))
            symbol = str(row.get("asset_symbol", "") or row.get("资产代码", "")).strip()
            name = str(row.get("asset_name", "") or row.get("资产名称", "")).strip() or symbol
            market = str(row.get("市场", ""))
            hist = get_position_history(asset_type, symbol)
            rsi = _compute_rsi(hist)
            volume_value = (
                row.get("成交量")
                if "成交量" in row
                else row.get("成交量(亿)")
                if "成交量(亿)" in row
                else row.get("成交量(万手)")
            )
            rows.append(
                {
                    "市场": market,
                    "代码": symbol,
                    "名称": name,
                    "现价": row.get("现价", ""),
                    "涨跌": row.get("涨跌额", ""),
                    "涨跌%": row.get("涨跌幅%", row.get("涨跌幅", "")),
                    "成交量": _format_volume_value(volume_value),
                    "RSI": round(rsi, 2) if rsi is not None else "",
                    "asset_type": asset_type,
                    "asset_symbol": symbol,
                    "asset_name": name,
                    "market_key": market_key,
                    "source_index": source_index,
                    "monitor_key": f"{market_key}:{symbol}",
                }
            )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if not monitor_order:
        watchlist_store.save_watchlist_monitor_order(df["monitor_key"].tolist())
        monitor_order_map = {key: idx for idx, key in enumerate(df["monitor_key"].tolist())}
    df["_monitor_order"] = df["monitor_key"].map(monitor_order_map)
    fallback_start = len(monitor_order_map)
    df["_monitor_order"] = [
        order if pd.notna(order) else fallback_start + idx
        for idx, order in enumerate(df["_monitor_order"])
    ]
    df = df.sort_values("_monitor_order").drop(columns="_monitor_order").reset_index(drop=True)
    return df


def extract_json_block(text: str) -> str:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if "\n" in raw:
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]
    return raw


def recognize_import_from_image(uploaded_file, mode: str) -> list[dict]:
    prompt_map = {
        "watchlist": """
请识别这张交易软件截图里的自选资产，返回严格 JSON，不要输出解释。
JSON 格式：
{"items":[{"market":"美国股票|中国股票|国际期货|国内期货","symbol":"代码","name":"名称"}]}
要求：
1. 只保留截图中明确可见的资产行。
2. symbol 尽量输出标准代码；中国股票保留 ts_code 格式，如 600519.SH。
3. 国内期货如果无法确认代码，可用常见品种名作为 symbol。
4. 无法判断的字段用空字符串，不要编造。
""",
        "positions": """
请识别这张持仓截图里的持仓资产，返回严格 JSON，不要输出解释。
JSON 格式：
{"items":[{"market":"美国股票|中国股票|国际期货|国内期货","symbol":"代码","name":"名称","quantity":0,"cost":0}]}
要求：
1. quantity 输出数字。
2. cost 输出持仓成本单价数字。
3. 只保留截图中明确可见的持仓行。
4. 无法判断的字段用空字符串或 0，不要编造。
""",
    }
    text = ai_client.image_chat(
        prompt=prompt_map[mode],
        image_bytes=uploaded_file.getvalue(),
        mime_type=ai_client.guess_mime_type(uploaded_file.name),
        api_key_claude=config.CLAUDE_API_KEY,
        max_tokens=2500,
    )
    payload = json.loads(extract_json_block(text) or "{}")
    items = payload.get("items", [])
    if not isinstance(items, list):
        return []
    return items

def make_flow_bar_svg(values: list, width: int = 200, height: int = 50) -> str:
    """生成资金流柱状图，正值自 0 轴向上，负值自 0 轴向下。"""
    if not values or len(values) < 2:
        return ""
    clean_values = [v for v in values if v == v]
    if len(clean_values) < 2:
        return ""

    n = len(clean_values)
    gap = 1
    bar_w = max(1.0, (width - gap * (n - 1)) / n)
    max_abs = max(abs(v) for v in clean_values) or 1
    zero_y = height / 2
    usable_half = max(1.0, zero_y - 2)

    rects = []
    for idx, v in enumerate(clean_values):
        x = idx * (bar_w + gap)
        bar_h = max(1.0, abs(v) / max_abs * usable_half)
        color = "#38f28b" if v >= 0 else "#ff6257"
        y = zero_y - bar_h if v >= 0 else zero_y
        rects.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" '
            f'rx="0.8" fill="{color}" opacity="0.9" />'
        )

    axis = (
        f'<line x1="0" y1="{zero_y:.2f}" x2="{width}" y2="{zero_y:.2f}" '
        f'stroke="rgba(142,163,189,0.28)" stroke-width="1" />'
    )
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="display:block;">{axis}{"".join(rects)}</svg>'
    )

@st.cache_data(ttl=3600)
def get_sparkline_prices_cn_index(ts_code: str, days: int = 30) -> list:
    """用 Tushare index_daily 获取 A股指数历史收盘价"""
    try:
        import tushare as ts
        from datetime import timedelta
        token = getattr(config, "TUSHARE_TOKEN", "") or ""
        if not token:
            return []
        pro = ts.pro_api(token=token)
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
        df = pro.index_daily(ts_code=ts_code, start_date=start, end_date=end,
                             fields="trade_date,close")
        if df is None or df.empty:
            return []
        df = df.sort_values("trade_date")
        return df["close"].dropna().tolist()[-days:]
    except Exception as e:
        print(f"[Sparkline] A股指数历史失败 {ts_code}: {e}")
        return []

def _build_sparklines_from_df(df: pd.DataFrame, name_col: str, code_col: str,
                               code_transform=None, days: int = 30) -> dict:
    """从 DataFrame 构建 {name: prices} sparkline 字典，code_transform 可选转换 symbol"""
    result = {}
    if code_col not in df.columns:
        return result
    for _, row in df.iterrows():
        name = str(row[name_col])
        sym = str(row[code_col])
        if code_transform:
            sym = code_transform(sym)
        prices = get_sparkline_prices(sym, days=days)
        result[name] = prices
    return result

def _legacy_make_sparkline_svg(prices: list, up: bool, width: int = 120, height: int = 40) -> str:
    """纯 CSS div 迷你柱状图，兼容所有 Streamlit 版本。"""
    if len(prices) < 2:
        return ""
    mn, mx = min(prices), max(prices)
    if mx == mn:
        return ""
    color = "#38f28b" if up else "#ff6257"
    n = len(prices)
    bar_w = max(1, width // n - 1)
    bars = "".join(
        f'<div style="display:inline-block;width:{bar_w}px;height:{max(1, int((p - mn) / (mx - mn) * height))}px;'
        f'background:{color};vertical-align:bottom;margin-right:1px;border-radius:1px;opacity:0.85;"></div>'
        for p in prices
    )
    return (
        f'<div style="width:{width}px;height:{height}px;display:flex;align-items:flex-end;'
        f'margin-top:6px;opacity:0.9;">{bars}</div>'
    )

def make_sparkline_svg(prices: list, up: bool, width: int = 120, height: int = 40) -> str:
    """生成轻量 SVG 折线 sparkline。"""
    if len(prices) < 2:
        return ""
    mn, mx = min(prices), max(prices)
    if mx == mn:
        return ""
    color = "#38f28b" if up else "#ff6257"
    step_x = width / (len(prices) - 1)
    points = []
    for idx, price in enumerate(prices):
        x = idx * step_x
        y = height - ((price - mn) / (mx - mn) * (height - 4)) - 2
        points.append(f"{x:.2f},{y:.2f}")

    polyline = " ".join(points)
    last_x, last_y = points[-1].split(",")
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="display:block;margin-top:6px;opacity:0.95;">'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />'
        f'<circle cx="{last_x}" cy="{last_y}" r="2.2" fill="{color}" />'
        f'</svg>'
    )

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_us_history(symbol, period, interval="1d"):
    return us_stocks.get_history(symbol, period=period, interval=interval)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_futures_history(symbol, period, interval="1d"):
    return futures.get_futures_history(symbol, period=period, interval=interval)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_global_market_snapshot():
    symbol_map = {
        "^GSPC": ("标普500", "美国", 18, 49),
        "^IXIC": ("纳斯达克", "美国", 16, 34),
        "^DJI": ("道琼斯", "美国", 16, 42),
        "^FTSE": ("富时100", "欧洲", 46, 28),
        "^GDAXI": ("德国DAX", "欧洲", 50, 28),
        "^FCHI": ("法国CAC", "欧洲", 47, 35),
        "^N225": ("日经", "亚洲", 87, 42),
        "^HSI": ("恒生指数", "亚洲", 79, 52),
        "000001.SS": ("上证", "亚洲", 81, 47),
        "^KS11": ("韩国指数", "亚洲", 84, 41),
        "^STI": ("新加坡", "亚洲", 77, 56),
        "^AXJO": ("ASX 200", "亚洲", 94, 70),
    }

    df = _disk_or_fetch(
        _rolling_cache_key("global_market_snapshot"),
        lambda: us_stocks.get_quote(list(symbol_map.keys())),
    )
    if df is None or df.empty:
        return pd.DataFrame()

    pct_col = get_pct_col(df)
    if pct_col is None:
        return pd.DataFrame()

    rows = []
    for _, row in df.iterrows():
        symbol = row.get("代码")
        if symbol not in symbol_map:
            continue
        display_name, region, x, y = symbol_map[symbol]
        pct_value = pd.to_numeric(row.get(pct_col), errors="coerce")
        if pd.isna(pct_value):
            continue
        rows.append(
            {
                "代码": symbol,
                "名称": display_name,
                "区域": region,
                "x": x,
                "y": y,
                "涨跌幅%": float(pct_value),
                "现价": row.get("现价", "—"),
            }
        )

    return pd.DataFrame(rows)


def load_telegram_hotspots():
    bot_token  = getattr(config, "TELEGRAM_BOT_TOKEN", "") or ""
    chat_id    = getattr(config, "TELEGRAM_CHAT_ID",   "") or ""
    claude_key = getattr(config, "CLAUDE_API_KEY",     "") or ""
    groq_key   = getattr(config, "GROQ_API_KEY",       "") or ""
    return telegram_feed.get_recent_messages(
        bot_token,
        chat_id,
        limit=12,
        claude_api_key=claude_key,
        groq_api_key=groq_key,
    )


def get_fragment_decorator(run_every: int | None = None):
    fragment_api = getattr(st, "fragment", None) or getattr(st, "experimental_fragment", None)
    if fragment_api is None:
        def passthrough(func):
            return func
        return passthrough
    return fragment_api(run_every=run_every)


def ensure_page_autorefresh():
    if st_autorefresh is not None:
        st_autorefresh(interval=max(int(config.REFRESH_INTERVAL), 30) * 1000, key="global_page_autorefresh")


# ─── 工具函数 ─────────────────────────────────────────────────────
def color_change(val):
    """给涨跌幅列上色"""
    try:
        v = float(val)
        if v > 0:
            return "color: #27AE60; font-weight: bold"
        elif v < 0:
            return "color: #E74C3C; font-weight: bold"
    except Exception:
        pass
    return "color: #7F8C8D"


def format_pct(val):
    try:
        v = float(val)
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.2f}%"
    except Exception:
        return str(val)


def format_refresh_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} 秒"
    if seconds % 60 == 0:
        return f"{seconds // 60} 分钟"
    return f"{seconds} 秒"


def style_table(df, pct_col="涨跌幅%"):
    """对 DataFrame 应用样式（保留兼容性）"""
    if df.empty:
        return df
    if pct_col not in df.columns:
        fallback_cols = ["涨跌幅%", "涨跌幅"]
        pct_col = next((col for col in fallback_cols if col in df.columns), None)
        if pct_col is None:
            return df.style.set_properties(**{"font-size": "13px"})
    styled = df.style.map(color_change, subset=[pct_col]) \
                     .format({pct_col: format_pct}) \
                     .set_properties(**{"font-size": "13px"})
    return styled


def render_table(
    df: pd.DataFrame,
    pct_col: str = "涨跌幅%",
    price_col: str = "现价",
    detail_type: str = "",
    symbol_col: str = "代码",
    name_col: str = "名称",
    clickable_cols: list[str] | None = None,
    key_prefix: str = "table",
):
    """用自定义 HTML 渲染行情表格，替代原生 st.dataframe。"""
    if df is None or df.empty:
        st.info("暂无数据")
        return

    # 找到实际的涨跌幅列
    actual_pct = next((c for c in [pct_col, "涨跌幅%", "涨跌幅"] if c in df.columns), None)

    if detail_type and clickable_cols:
        header_cols = st.columns(len(df.columns))
        for col_ui, col_name in zip(header_cols, df.columns):
            with col_ui:
                st.markdown(
                    f'<div style="padding:0.35rem 0.2rem 0.55rem 0.2rem;font-size:0.75rem;'
                    f'font-weight:500;color:#5a7a9a;letter-spacing:0.05em;text-transform:uppercase;">'
                    f'{html_lib.escape(str(col_name))}</div>',
                    unsafe_allow_html=True,
                )

        for row_idx, (_, row) in enumerate(df.iterrows()):
            row_cols = st.columns(len(df.columns))
            detail_symbol = str(row.get(symbol_col, "")).strip() if symbol_col and symbol_col in df.columns else ""
            if detail_type == "us_stock" and "代码" in df.columns:
                detail_symbol = str(row.get("代码", detail_symbol)).strip()
            if detail_type == "intl_future" and not detail_symbol and name_col in df.columns:
                intl_symbol_map = {name: sym for sym, name in futures.get_all_symbols()}
                detail_symbol = str(intl_symbol_map.get(str(row.get(name_col, "")).strip(), "")).strip()
            detail_name = str(row.get(name_col, detail_symbol or "")) if name_col in df.columns else detail_symbol

            for col_ui, col_name in zip(row_cols, df.columns):
                val = row[col_name]
                display = html_lib.escape(str(val))
                style = "font-size:0.9rem;color:#c8d8ea;padding:0.45rem 0.2rem;"

                if (
                    detail_type == "us_stock"
                    and col_name == name_col
                    and "代码" in df.columns
                ):
                    code_val = str(row.get("代码", "")).strip()
                    if code_val and str(val).strip() == code_val:
                        display = html_lib.escape(us_stocks.STOCK_DISPLAY_NAMES.get(code_val, code_val))

                if col_name == actual_pct:
                    try:
                        v = float(val)
                        if v > 0:
                            display = f"+{v:.2f}%"
                            style = "font-size:0.9rem;color:#38f28b;font-weight:700;padding:0.45rem 0.2rem;"
                        elif v < 0:
                            display = f"{v:.2f}%"
                            style = "font-size:0.9rem;color:#ff6257;font-weight:700;padding:0.45rem 0.2rem;"
                        else:
                            display = f"{v:.2f}%"
                            style = "font-size:0.9rem;color:#8ea3bd;padding:0.45rem 0.2rem;"
                    except Exception:
                        pass
                elif col_name == price_col or col_name == "现价":
                    style = "font-size:0.9rem;color:#eaf2ff;font-weight:700;padding:0.45rem 0.2rem;"
                elif col_name in ("涨跌额",):
                    try:
                        v = float(val)
                        display = f"+{v:.2f}" if v > 0 else f"{v:.2f}"
                        style = f"font-size:0.9rem;color:{'#38f28b' if v > 0 else '#ff6257' if v < 0 else '#8ea3bd'};padding:0.45rem 0.2rem;"
                    except Exception:
                        pass

                with col_ui:
                    if col_name in clickable_cols and detail_symbol:
                        if st.button(str(val), key=f"{key_prefix}_{detail_type}_{detail_symbol}_{row_idx}_{col_name}", use_container_width=True):
                            st.session_state["selected_asset"] = {
                                "symbol": detail_symbol,
                                "name": detail_name,
                                "type": detail_type,
                            }
                            st.session_state["detail_request_id"] = st.session_state.get("detail_request_id", 0) + 1
                            st.rerun()
                    else:
                        st.markdown(f'<div style="{style}">{display}</div>', unsafe_allow_html=True)
            st.markdown('<div style="height:1px;background:rgba(110,170,255,0.06);margin:0.05rem 0 0.05rem 0;"></div>', unsafe_allow_html=True)
        return

    header_cells = "".join(f'<th>{html_lib.escape(str(c))}</th>' for c in df.columns)

    rows_html = ""
    table_triggers = []
    for _, row in df.iterrows():
        cells = ""
        detail_symbol = str(row.get(symbol_col, "")).strip() if symbol_col and symbol_col in df.columns else ""
        if detail_type == "us_stock" and "代码" in df.columns:
            detail_symbol = str(row.get("代码", detail_symbol)).strip()
        if detail_type == "intl_future" and not detail_symbol and name_col in df.columns:
            intl_symbol_map = {name: sym for sym, name in futures.get_all_symbols()}
            detail_symbol = str(intl_symbol_map.get(str(row.get(name_col, "")).strip(), "")).strip()
        detail_name = str(row.get(name_col, detail_symbol or "")) if name_col in df.columns else detail_symbol
        trigger_id = ""
        row_trigger_attr = ""
        if detail_type and detail_symbol:
            trigger_token = quote(f"{detail_type}:{detail_symbol}", safe="").replace("%", "_")
            trigger_id = f"__t{trigger_token}"
            row_trigger_attr = f' data-trigger="{trigger_id}" id="item-{trigger_token}"'
            table_triggers.append((trigger_id, detail_symbol, detail_name, detail_type))
        for col in df.columns:
            val = row[col]
            cell_style = ""
            display = html_lib.escape(str(val))

            if (
                detail_type == "us_stock"
                and col == name_col
                and "代码" in df.columns
            ):
                code_val = str(row.get("代码", "")).strip()
                if code_val and str(val).strip() == code_val:
                    display = html_lib.escape(us_stocks.STOCK_DISPLAY_NAMES.get(code_val, code_val))

            if col == actual_pct:
                try:
                    v = float(val)
                    if v > 0:
                        cell_style = "color:#38f28b;font-weight:600;"
                        display = f"+{v:.2f}%"
                    elif v < 0:
                        cell_style = "color:#ff6257;font-weight:600;"
                        display = f"{v:.2f}%"
                    else:
                        cell_style = "color:#8ea3bd;"
                        display = f"{v:.2f}%"
                except Exception:
                    pass
            elif col == price_col or col == "现价":
                cell_style = "color:#eaf2ff;font-weight:600;font-variant-numeric:tabular-nums;"
            elif col in ("涨跌额",):
                try:
                    v = float(val)
                    cell_style = "color:#38f28b;" if v > 0 else ("color:#ff6257;" if v < 0 else "color:#8ea3bd;")
                    display = f"+{v:.2f}" if v > 0 else f"{v:.2f}"
                except Exception:
                    pass

            if trigger_id and col in (clickable_cols or [name_col, symbol_col]):
                display = (
                    f'<span{row_trigger_attr} style="cursor:pointer;text-decoration:none;'
                    f'font-weight:700;color:#dfe9f8;">{display}</span>'
                )
            cells += f'<td style="{cell_style}">{display}</td>'
        rows_html += f"<tr>{cells}</tr>"

    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:12px;border:1px solid rgba(110,170,255,0.12);background:rgba(10,16,28,0.7);">
    <table style="width:100%;border-collapse:collapse;font-size:0.88rem;color:#c8d8ea;">
        <thead>
            <tr style="border-bottom:1px solid rgba(110,170,255,0.18);background:rgba(73,198,255,0.05);">
                {header_cells}
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    </div>
    <style>
    table td, table th {{
        padding: 0.6rem 1rem;
        text-align: left;
        white-space: nowrap;
    }}
    table th {{
        font-size: 0.75rem;
        font-weight: 500;
        color: #5a7a9a;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}
    table tbody tr {{
        border-bottom: 1px solid rgba(110,170,255,0.06);
        transition: background 0.15s;
    }}
    table tbody tr:hover {{
        background: rgba(73,198,255,0.05);
    }}
    table tbody tr:last-child {{
        border-bottom: none;
    }}
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div data-detail-scope="table"></div>', unsafe_allow_html=True)
    for trigger_id, detail_symbol, detail_name, detail_type in table_triggers:
        if st.button(trigger_id, key=f"table_{detail_type}_{detail_symbol}"):
            st.session_state["selected_asset"] = {
                "symbol": detail_symbol,
                "name": detail_name,
                "type": detail_type,
            }
            st.session_state["detail_request_id"] = st.session_state.get("detail_request_id", 0) + 1
            st.rerun()


def get_pct_col(df: pd.DataFrame, preferred: str = "涨跌幅%") -> str | None:
    candidates = [preferred, "涨跌幅%", "涨跌幅"]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def render_hero(title: str, text: str, kicker: str = "Market Monitor"):
    st.markdown(
        f"""
        <div class="hero-panel">
            <div class="hero-kicker">{kicker}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_strip(cards: list[dict], title: str = "📡 市场温度计"):
    if not cards:
        return
    with st.container(border=True):
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
        cols = st.columns(len(cards))
        for col, card in zip(cols, cards):
            with col:
                st.markdown(
                    f"""
                    <div class="status-card">
                        <div class="status-label">{html_lib.escape(str(card['label']))}</div>
                        <div class="status-value" style="color:{html_lib.escape(str(card.get('color', '#f2f7ff')))};">{html_lib.escape(str(card['value']))}</div>
                        <div class="status-note">{html_lib.escape(str(card['note']))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_micro_status(items: list[dict]):
    if not items:
        return
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            color = html_lib.escape(str(item['color']))
            label = html_lib.escape(str(item['label']))
            value = html_lib.escape(str(item['value']))
            st.markdown(
                f"""
                <div class="micro-pill">
                    <span class="micro-dot" style="background:{color};"></span>
                    <span>{label}：{value}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_news_cards(df: pd.DataFrame):
    if df is None or df.empty:
        st.markdown(
            """
            <div class="news-empty">
                Telegram 热点消息待连接。填入 <code>TELEGRAM_BOT_TOKEN</code> 和
                <code>TELEGRAM_CHAT_ID</code> 后，这里会自动同步最近消息。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    records = list(df.to_dict(orient="records"))
    for start in range(0, len(records), 3):
        row_items = records[start:start + 3]
        cols = st.columns(3)
        for idx, col in enumerate(cols):
            if idx >= len(row_items):
                continue
            row = row_items[idx]
            title = html_lib.escape(str(row.get("标题", "未命名消息")))
            body = html_lib.escape(str(row.get("内容", ""))).replace("\n", "<br>")
            source = html_lib.escape(str(row.get("来源", "Telegram")))
            date_str = html_lib.escape(str(row.get("日期", "")))
            time_str = html_lib.escape(str(row.get("时间", "")))
            with col:
                st.markdown(
                    f"""
                    <div class="news-card">
                        <div class="news-meta">
                            <span class="news-source">{source}</span>
                            <span class="news-time">{date_str} {time_str}</span>
                        </div>
                        <div class="news-title">{title}</div>
                        <div class="news-body">{body}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


@get_fragment_decorator(run_every=config.REFRESH_INTERVAL)
def render_hot_news_panel():
    refresh_btn_key = "hot_news_manual_refresh_btn"
    if st.session_state.pop(refresh_btn_key, False):
        load_telegram_hotspots.clear()

    new_df = load_telegram_hotspots()

    # 累积消息到 session_state，避免每次刷新丢失历史条目
    _key = "_tg_msg_cache"
    success_key = "_tg_msg_last_success_at"
    prev_df = st.session_state.get(_key, pd.DataFrame())
    if not new_df.empty:
        combined = pd.concat([new_df, prev_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["标题", "时间", "日期"])
        st.session_state[_key] = combined.head(20)
        st.session_state[success_key] = time.time()
    expand_key = "_hot_news_expand_all"
    all_df = st.session_state.get(_key, new_df)
    display_limit = 12 if st.session_state.get(expand_key, False) else 6
    display_df = all_df.head(display_limit)
    last_success_at = st.session_state.get(success_key)

    with st.container(border=True):
        header_cols = st.columns([1, 0.45])
        with header_cols[0]:
            st.markdown('<div class="section-title">🗞 热点消息</div>', unsafe_allow_html=True)
            if last_success_at:
                st.caption(f"上次成功刷新：{datetime.fromtimestamp(last_success_at).strftime('%Y-%m-%d %H:%M:%S')}")
        with header_cols[1]:
            if st.button("Refresh Now", key="hot_news_refresh_now", use_container_width=True):
                st.session_state[refresh_btn_key] = True
                st.rerun()

        if new_df.empty and last_success_at and time.time() - float(last_success_at) > config.REFRESH_INTERVAL * 3:
            st.warning("热点消息暂时没有成功刷新，当前展示的是上次抓取到的缓存内容。")
        render_news_cards(display_df)
        if len(all_df) > 6:
            action_cols = st.columns([1, 1, 1])
            with action_cols[2]:
                button_label = "Collapse" if st.session_state.get(expand_key, False) else "Expand All"
                if st.button(button_label, key="hot_news_expand_all_btn", use_container_width=True):
                    st.session_state[expand_key] = not st.session_state.get(expand_key, False)
                    st.rerun()


TICKER_DOMAIN = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "NVDA": "nvidia.com",
    "GOOGL": "abc.xyz", "GOOG": "abc.xyz", "META": "meta.com",
    "AMZN": "amazon.com", "TSLA": "tesla.com", "BABA": "alibaba.com",
    "PDD": "pddholdings.com", "NFLX": "netflix.com", "AMD": "amd.com",
    "INTC": "intel.com", "ORCL": "oracle.com", "CRM": "salesforce.com",
    "UBER": "uber.com", "SHOP": "shopify.com", "PYPL": "paypal.com",
    "DIS": "disney.com", "BRKB": "berkshirehathaway.com",
}

def render_market_heatmap(df: pd.DataFrame, title: str, name_col: str = "名称"):
    pct_col = get_pct_col(df)
    if df is None or df.empty or pct_col is None or name_col not in df.columns:
        st.info("当前暂无可用于热力图的数据")
        return

    heatmap_df = df.copy()
    heatmap_df[pct_col] = pd.to_numeric(heatmap_df[pct_col], errors="coerce")
    heatmap_df = heatmap_df.dropna(subset=[pct_col])
    if heatmap_df.empty:
        st.info("当前暂无可用于热力图的数据")
        return

    if "市值(亿)" in heatmap_df.columns:
        heatmap_df["_size"] = pd.to_numeric(heatmap_df["市值(亿)"], errors="coerce").fillna(1)
    else:
        heatmap_df["_size"] = 1
    heatmap_df["_size"] = heatmap_df["_size"].where(heatmap_df["_size"] > 0, 1)

    total = heatmap_df["_size"].sum()

    tiles = ""
    heatmap_triggers = []
    for _, row in heatmap_df.sort_values("_size", ascending=False).iterrows():
        ticker = str(row.get("代码", row[name_col]))
        pct = float(row[pct_col])
        size_pct = row["_size"] / total * 100
        token_source = f"us_stock:{ticker}"
        trigger_token = quote(token_source, safe="").replace("%", "_")
        trigger_id = f"__t{trigger_token}"
        card_id = f"card-{trigger_token}"
        heatmap_triggers.append((trigger_id, ticker, str(row.get(name_col, ticker))))

        if pct > 1.5:
            bg = "#1a7a4a"
        elif pct > 0:
            bg = "#1f5c3a"
        elif pct > -1.5:
            bg = "#6b2d2d"
        else:
            bg = "#8b1a1a"

        domain = TICKER_DOMAIN.get(ticker, "")
        logo_html = (
            f'<img src="https://logo.clearbit.com/{domain}" '
            f'style="width:28px;height:28px;border-radius:6px;object-fit:contain;'
            f'background:#fff;padding:2px;display:none;" '
            f'onload="this.style.display=\'block\'" onerror="this.remove()">'
            if domain else ""
        )

        pct_str = f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%"
        pct_color = "#5effa0" if pct >= 0 else "#ff7b72"

        tiles += f"""
        <div id="{card_id}" data-trigger="{trigger_id}" style="flex:{size_pct:.1f} 1 {max(size_pct*1.2, 80):.0f}px;
                    min-width:80px;min-height:90px;
                    background:{bg};border-radius:8px;
                    padding:10px 10px 8px 10px;
                    display:flex;flex-direction:column;justify-content:space-between;
                    position:relative;overflow:hidden;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <span style="font-weight:700;font-size:0.95rem;color:#e8f4ea;">{html_lib.escape(ticker)}</span>
                {logo_html}
            </div>
            <span style="font-size:1.05rem;font-weight:600;color:{pct_color};">{pct_str}</span>
        </div>"""

    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:3px;width:100%;">{tiles}</div>',
        unsafe_allow_html=True,
    )
    for trigger_id, symbol, display_name in heatmap_triggers:
        if st.button(trigger_id, key=f"heatmap_{symbol}"):
            st.session_state["selected_asset"] = {
                "symbol": symbol,
                "name": display_name,
                "type": "us_stock",
            }
            st.session_state["detail_request_id"] = st.session_state.get("detail_request_id", 0) + 1
            st.rerun()


def get_world_map_background_uri() -> str:
    image_path = os.path.join(os.path.dirname(__file__), "pic", "Globalmap.png")
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _is_mobile_request() -> bool:
    try:
        headers = dict(st.context.headers)
    except Exception:
        headers = {}
    user_agent = str(headers.get("User-Agent", headers.get("user-agent", ""))).lower()
    if not user_agent:
        return False
    return any(token in user_agent for token in ["iphone", "android", "mobile", "ipad"])


def _box_overlaps(box_a: dict, box_b: dict, padding: float = 0.0) -> bool:
    return not (
        box_a["x1"] + padding < box_b["x0"]
        or box_a["x0"] - padding > box_b["x1"]
        or box_a["y1"] + padding < box_b["y0"]
        or box_a["y0"] - padding > box_b["y1"]
    )


def _make_text_box(center_x: float, top_y: float, width: float, height: float) -> dict:
    half_w = width / 2
    return {
        "x0": center_x - half_w,
        "x1": center_x + half_w,
        "y0": top_y,
        "y1": top_y + height,
    }


def _build_global_map_positions(bubble_df: pd.DataFrame, position_map: dict, mobile_mode: bool) -> dict:
    candidate_offsets = [
        (0, -8),
        (7, -6),
        (-7, -6),
        (8, -1),
        (-8, -1),
        (0, 4),
        (9, 5),
        (-9, 5),
    ] if mobile_mode else [
        (0, -6),
        (6, -4),
        (-6, -4),
        (7, 0),
        (-7, 0),
        (0, 4),
        (8, 4),
        (-8, 4),
    ]
    mobile_priority_positions = {
        "纳斯达克": {"label": (17.2, 30.0), "pct": (17.2, 33.1)},
        "道琼斯": {"label": (11.6, 40.8), "pct": (11.6, 43.9)},
        "标普500": {"label": (21.8, 38.3), "pct": (21.8, 41.4)},
        "富时100": {"label": (44.0, 26.0), "pct": (44.0, 29.1)},
        "德国DAX": {"label": (55.8, 26.0), "pct": (55.8, 29.1)},
        "法国CAC": {"label": (46.6, 42.0), "pct": (46.6, 45.1)},
        "韩国指数": {"label": (86.0, 38.0), "pct": (86.0, 41.1)},
        "上证": {"label": (78.0, 49.5), "pct": (78.0, 52.6)},
        "日经": {"label": (89.4, 49.0), "pct": (89.4, 52.1)},
        "恒生指数": {"label": (81.5, 60.0), "pct": (81.5, 63.1)},
        "新加坡": {"label": (76.0, 69.0), "pct": (76.0, 72.1)},
        "ASX 200": {"label": (90.5, 78.0), "pct": (90.5, 81.1)},
    }
    all_dots = [(float(row["plot_x"]), float(row["plot_y"])) for _, row in bubble_df.iterrows()]
    crowded_rows = []
    for _, row in bubble_df.iterrows():
        dot_x = float(row["plot_x"])
        dot_y = float(row["plot_y"])
        nearby_count = sum(
            1
            for other_x, other_y in all_dots
            if (other_x, other_y) != (dot_x, dot_y) and abs(other_x - dot_x) <= 12 and abs(other_y - dot_y) <= 12
        )
        crowded_rows.append((nearby_count, row))

    placed_boxes = []
    mobile_positions = {}
    for _, row in sorted(crowded_rows, key=lambda item: (-item[0], float(item[1]["plot_x"]))):
        name = row["名称"]
        dot_x = float(row["plot_x"])
        dot_y = float(row["plot_y"])
        base_pos = position_map.get(
            name,
            {"dot": (dot_x, dot_y), "label": (dot_x, dot_y - 5), "pct": (dot_x, dot_y - 2)},
        )
        if mobile_mode and name in mobile_priority_positions:
            base_pos = {
                **base_pos,
                "label": mobile_priority_positions[name]["label"],
                "pct": mobile_priority_positions[name]["pct"],
            }
        base_dx = round(float(base_pos["label"][0]) - dot_x, 1)
        base_dy = round(float(base_pos["label"][1]) - dot_y, 1)
        preferred_offsets = [(base_dx, base_dy)] + [offset for offset in candidate_offsets if offset != (base_dx, base_dy)]

        cluster_width = max(8.0, len(str(name)) * 1.9, 8.8)
        cluster_height = 7.2
        best_layout = None
        best_score = None
        for dx, dy in preferred_offsets:
            label_x = dot_x + dx
            label_y = dot_y + dy
            pct_x = label_x
            pct_y = label_y + 2.8
            combined_box = _make_text_box(label_x, label_y - 1.4, cluster_width, cluster_height)
            score = abs(dx) * 0.5 + abs(dy) * 0.65

            if combined_box["x0"] < 2:
                score += (2 - combined_box["x0"]) * 12
            if combined_box["x1"] > 98:
                score += (combined_box["x1"] - 98) * 12
            if combined_box["y0"] < 3:
                score += (3 - combined_box["y0"]) * 12
            if combined_box["y1"] > 97:
                score += (combined_box["y1"] - 97) * 12

            for box in placed_boxes:
                if _box_overlaps(combined_box, box, padding=0.8):
                    score += 80

            for other_x, other_y in all_dots:
                if (other_x, other_y) == (dot_x, dot_y):
                    continue
                if (
                    combined_box["x0"] - 1.2 <= other_x <= combined_box["x1"] + 1.2
                    and combined_box["y0"] - 1.2 <= other_y <= combined_box["y1"] + 1.2
                ):
                    score += 28

            if best_score is None or score < best_score:
                best_score = score
                best_layout = {
                    "dot": (dot_x, dot_y),
                    "label": (label_x, label_y),
                    "pct": (pct_x, pct_y),
                    "box": combined_box,
                }

        mobile_positions[name] = {
            "dot": best_layout["dot"],
            "label": best_layout["label"],
            "pct": best_layout["pct"],
        }
        placed_boxes.append(best_layout["box"])

    return {**position_map, **mobile_positions}


def render_global_bubble_map(df: pd.DataFrame):
    if df is None or df.empty:
        st.info("当前暂无全球市场追踪图数据")
        return

    bubble_df = df.copy()
    bubble_df["涨跌幅%"] = pd.to_numeric(bubble_df["涨跌幅%"], errors="coerce")
    bubble_df = bubble_df.dropna(subset=["涨跌幅%"])
    if bubble_df.empty:
        st.info("当前暂无全球市场追踪图数据")
        return

    position_map = {
        "纳斯达克": {"dot": (18, 34), "label": (18, 28), "pct": (18, 31)},
        "道琼斯": {"dot": (16, 42), "label": (14, 36), "pct": (14, 39)},
        "标普500": {"dot": (20, 40), "label": (22, 35), "pct": (22, 38)},
        "富时100": {"dot": (46, 31), "label": (43, 25), "pct": (43, 28)},
        "德国DAX": {"dot": (50, 31), "label": (53, 25), "pct": (53, 28)},
        "法国CAC": {"dot": (47, 35), "label": (47, 39), "pct": (47, 42)},
        "恒生指数": {"dot": (79, 47), "label": (80, 52), "pct": (80, 55)},
        "上证": {"dot": (81, 44), "label": (78, 41), "pct": (78, 44)},
        "韩国指数": {"dot": (82, 40), "label": (82, 34), "pct": (82, 37)},
        "日经": {"dot": (84, 42), "label": (87, 42), "pct": (87, 45)},
        "新加坡": {"dot": (77, 56), "label": (76, 61), "pct": (76, 64)},
        "ASX 200": {"dot": (90.2, 70), "label": (87.4, 70), "pct": (87.4, 73)},
    }
    mobile_mode = _is_mobile_request()
    bubble_df["plot_x"] = bubble_df["名称"].map(lambda name: position_map.get(name, {"dot": (50, 50)})["dot"][0])
    bubble_df["plot_y"] = bubble_df["名称"].map(lambda name: position_map.get(name, {"dot": (50, 50)})["dot"][1])
    bubble_df["display_color"] = bubble_df["涨跌幅%"].apply(
        lambda value: "#38f28b" if value > 0 else "#ff6257" if value < 0 else "#ffffff"
    )
    label_positions = _build_global_map_positions(bubble_df, position_map, mobile_mode)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=bubble_df["plot_x"],
            y=bubble_df["plot_y"],
            mode="markers",
            customdata=bubble_df[["名称", "涨跌幅%", "现价", "区域"]],
            hovertemplate="<b>%{customdata[0]}</b><br>区域: %{customdata[3]}<br>涨跌幅: %{customdata[1]:+.2f}%<br>现价: %{customdata[2]}<extra></extra>",
            marker=dict(
                size=4,
                color=bubble_df["display_color"],
                line=dict(color=bubble_df["display_color"], width=1.2),
                opacity=0.5,
            ),
        )
    )
    for _, row in bubble_df.iterrows():
        text_color = row["display_color"]
        pos = label_positions.get(
            row["名称"],
            {"label": (row["plot_x"], row["plot_y"] - 2), "pct": (row["plot_x"], row["plot_y"] + 1)},
        )
        fig.add_annotation(
            x=pos["label"][0],
            y=pos["label"][1],
            text=row["名称"],
            showarrow=False,
            font=dict(size=11 if mobile_mode else 13, color=text_color, family="Arial Black"),
            xanchor="center",
            yanchor="middle",
            align="center",
        )
        fig.add_annotation(
            x=pos["pct"][0],
            y=pos["pct"][1],
            text=f"{row['涨跌幅%']:+.2f}%",
            showarrow=False,
            font=dict(size=11 if mobile_mode else 13, color=text_color, family="Arial Black"),
            xanchor="center",
            yanchor="middle",
            align="center",
        )
    fig.update_layout(
        height=470 if mobile_mode else 430,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="#121417",
        plot_bgcolor="#121417",
        xaxis=dict(visible=False, range=[0, 100], fixedrange=True),
        yaxis=dict(visible=False, range=[100, 0], fixedrange=True),
        showlegend=False,
        dragmode=False,
        images=[
            dict(
                source=get_world_map_background_uri(),
                xref="paper",
                yref="paper",
                x=0,
                y=1,
                sizex=1,
                sizey=1,
                sizing="stretch",
                opacity=1,
                layer="below",
            )
        ],
        shapes=[
            dict(
                type="rect",
                xref="paper",
                yref="paper",
                x0=0,
                y0=0,
                x1=1,
                y1=1,
                fillcolor="rgba(2, 8, 15, 0.5)",
                line=dict(width=0),
                layer="below",
            )
        ],
        annotations=[],
    )
    st.plotly_chart(
        fig,
        width='stretch',
        config={
            "displayModeBar": False,
            "scrollZoom": False,
            "doubleClick": False,
            "responsive": True,
        },
    )


from contextlib import contextmanager

@contextmanager
def panel(title: str):
    with st.container(border=True):
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
        yield


# 保留旧接口兼容性（热点消息等地方仍在用）
def open_panel(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

def close_panel():
    pass


def summarize_market(
    us_idx: pd.DataFrame,
    cn_idx: pd.DataFrame,
    intl_fut_df: pd.DataFrame,
    cn_fut_df: pd.DataFrame,
) -> list[dict]:
    def describe(df: pd.DataFrame, label: str):
        pct_col = get_pct_col(df)
        if df is None or df.empty or pct_col is None:
            return {"label": label, "value": "数据待连接", "note": "当前环境暂无可用行情"}
        numeric = pd.to_numeric(df[pct_col], errors="coerce").dropna()
        if numeric.empty:
            return {"label": label, "value": "监控中", "note": "报价结构已返回，等待可用数值"}
        avg = numeric.mean()
        breadth = f"{(numeric > 0).sum()}/{len(numeric)} 上涨"
        tone = "偏强" if avg > 0.4 else "承压" if avg < -0.4 else "震荡"
        color_word = "红盘" if avg > 0 else "绿盘" if avg < 0 else "平衡"
        return {"label": label, "value": tone, "note": f"{color_word}均值 {avg:+.2f}% · {breadth}"}

    cards = [
        describe(us_idx, "美国市场"),
        describe(cn_idx, "中国市场"),
        describe(fut_df, "商品与期货"),
    ]
    return cards


def summarize_market_breadth(
    us_idx: pd.DataFrame,
    cn_idx: pd.DataFrame,
    intl_fut_df: pd.DataFrame,
    cn_fut_df: pd.DataFrame,
) -> list[dict]:
    def describe(df: pd.DataFrame, label: str) -> dict:
        pct_col = get_pct_col(df)
        if df is None or df.empty or pct_col is None:
            return {"label": label, "value": "--", "note": "当前暂无可用行情", "color": "#8ea3bd"}
        numeric = pd.to_numeric(df[pct_col], errors="coerce").dropna()
        if numeric.empty:
            return {"label": label, "value": "--", "note": "报价结构暂不可用", "color": "#8ea3bd"}
        up_count = int((numeric > 0).sum())
        total = int(len(numeric))
        up_ratio = up_count / total if total else 0
        return {
            "label": label,
            "value": f"{up_ratio:.0%} 上涨",
            "note": f"{up_count}/{total} 上涨",
            "color": "#38f28b" if up_ratio >= 0.5 else "#ff6257",
        }

    return [
        describe(us_idx, "美国市场"),
        describe(cn_idx, "中国市场"),
        describe(intl_fut_df, "国际期货"),
        describe(cn_fut_df, "国内期货"),
    ]


def render_sector_heatmap(df: pd.DataFrame, constituent_df: pd.DataFrame | None = None):
    """渲染美股板块层级热力图：板块 -> 代表成分股。"""
    if df is None or df.empty:
        st.info("暂无板块数据")
        return

    df = df.copy()
    df["涨跌幅%"] = pd.to_numeric(df["涨跌幅%"], errors="coerce").fillna(0)
    df["AUM"] = pd.to_numeric(df.get("AUM", 1e9), errors="coerce").fillna(1e9)

    if constituent_df is None or constituent_df.empty:
        constituent_df = pd.DataFrame()

    labels, parents, values, colors, texts, ids = [], [], [], [], [], []

    def _color_for_pct(pct: float) -> str:
        if pct > 1.5:
            return "#1a7a4a"
        if pct > 0:
            return "#1f5c3a"
        if pct > -1.5:
            return "#6b2d2d"
        return "#8b1a1a"

    for _, row in df.iterrows():
        sector = str(row["板块"])
        sector_pct = float(row["涨跌幅%"])
        sector_value = float(row["AUM"])
        sector_id = f"sector:{sector}"

        labels.append(sector)
        parents.append("")
        values.append(sector_value)
        colors.append(_color_for_pct(sector_pct))
        texts.append(f"{sector}<br>{sector_pct:+.2f}%")
        ids.append(sector_id)

        if constituent_df.empty:
            continue
        sub = constituent_df[constituent_df["板块"] == sector].copy()
        if sub.empty:
            continue
        sub["权重"] = pd.to_numeric(sub["权重"], errors="coerce").fillna(1.0)
        weight_sum = sub["权重"].sum() or 1.0
        for _, srow in sub.iterrows():
            sym = str(srow["代码"])
            pct = float(pd.to_numeric(srow["涨跌幅%"], errors="coerce") or 0)
            child_value = sector_value * (float(srow["权重"]) / weight_sum)
            labels.append(sym)
            parents.append(sector_id)
            values.append(child_value)
            colors.append(_color_for_pct(pct))
            texts.append(f"{sym}<br>{pct:+.2f}%")
            ids.append(f"{sector_id}:{sym}")

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        text=texts,
        texttemplate="%{text}",
        marker=dict(colors=colors, line=dict(width=2, color="#07111b")),
        textfont=dict(color="#edf4ff", size=13),
        hovertemplate="<b>%{label}</b><extra></extra>",
        maxdepth=2,
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

def render_earnings_calendar(df: pd.DataFrame):
    """渲染财报日历：按日期分组，每天一列"""
    if df is None or df.empty:
        st.info("未来 30 天内自选股暂无已知财报日期")
        return

    grouped = df.groupby("日期")
    date_list = sorted(grouped.groups.keys())
    cols = st.columns(len(date_list))

    for col, d in zip(cols, date_list):
        symbols = grouped.get_group(d)["代码"].tolist()
        weekday = WEEKDAY_CN[d.weekday()]
        with col:
            st.markdown(
                f'<div style="background:#0d1f35;border-radius:10px;padding:12px 14px;">'
                f'<div style="font-size:1.3rem;font-weight:700;color:#edf4ff;">{d.month}月{d.day}日'
                f'<span style="font-size:0.8rem;color:#8ea3bd;margin-left:6px;">{weekday}</span></div>',
                unsafe_allow_html=True,
            )
            for sym in symbols:
                trigger_token = quote(f"us_stock:{sym}", safe="").replace("%", "_")
                trigger_id = f"__t{trigger_token}"
                domain = TICKER_DOMAIN.get(sym, "")
                logo = (
                    f'<img src="https://logo.clearbit.com/{domain}" '
                    f'style="width:24px;height:24px;border-radius:5px;object-fit:contain;'
                    f'background:#fff;padding:2px;display:none;vertical-align:middle;" '
                    f'onload="this.style.display=\'inline-block\'" onerror="this.remove()">'
                    if domain else
                    f'<span style="display:inline-block;width:24px;height:24px;border-radius:5px;'
                    f'background:#1e3a5f;text-align:center;line-height:24px;font-size:0.65rem;'
                    f'color:#8ea3bd;">{sym[:2]}</span>'
                )
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin-top:8px;">'
                    f'{logo}'
                    f'<span id="item-{trigger_token}" data-trigger="{trigger_id}" '
                    f'style="font-weight:600;color:#dfe9f8;font-size:0.9rem;cursor:pointer;">{sym}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(trigger_id, key=f"earnings_{sym}"):
                    st.session_state["selected_asset"] = {
                        "symbol": sym,
                        "name": sym,
                        "type": "us_stock",
                    }
                    st.session_state["detail_request_id"] = st.session_state.get("detail_request_id", 0) + 1
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


@st.dialog("📊 资产详情", width="large")
def show_asset_detail(symbol: str, display_name: str, asset_type: str = "us_stock"):
    """点击卡片后弹出统一详情：K线 + AI 复盘/前景 or 财报分析。"""
    st.markdown(f"### {display_name}")
    if symbol:
        st.caption(symbol)

    type_label_map = {
        "us_stock": "美股",
        "us_index": "美股指数",
        "cn_stock": "A股",
        "cn_index": "A股指数",
        "intl_future": "国际期货",
        "cn_future": "国内期货",
    }
    st.caption(f"资产类型：{type_label_map.get(asset_type, asset_type)}")

    with st.spinner("加载K线数据…"):
        if asset_type in ("us_stock", "us_index"):
            hist = load_us_history(symbol, "2y")
        elif asset_type == "cn_stock":
            hist = load_cn_history(symbol)
        elif asset_type == "intl_future":
            hist = load_futures_history(symbol, "2y")
        elif asset_type == "cn_index":
            hist = load_cn_history(symbol)
        elif asset_type == "cn_future":
            hist = load_cn_futures_history(symbol)
        else:
            hist = pd.DataFrame()

    if hist.empty:
        st.info("暂无K线数据")
        return

    kline_key = get_kline_cache_key(hist, symbol=symbol, asset_type=asset_type)

    st.divider()

    if asset_type == "us_stock":
        st.markdown("**📅 下一份财报时间**")
        try:
            import yfinance as yf

            cal = yf.Ticker(symbol).calendar
            if cal and isinstance(cal, dict):
                dates = cal.get("Earnings Date") or []
                if dates:
                    next_date = pd.Timestamp(dates[0]).strftime("%Y-%m-%d")
                    st.markdown(f"下次财报：**{next_date}**")
                else:
                    st.markdown("暂无财报日期")
            else:
                st.markdown("暂无财报日期")
        except Exception:
            st.markdown("暂无财报日期")

        st.markdown("**🤖 AI 财报与前景分析**")
        with st.spinner("生成股票 AI 分析…"):
            st.markdown(get_ai_stock_detail(symbol, display_name, kline_key, hist))
    else:
        st.markdown("**🤖 AI 走势复盘与前景分析**")
        with st.spinner("生成资产 AI 分析…"):
            st.markdown(get_ai_market_asset_analysis(symbol, display_name, asset_type, kline_key, hist))

    st.divider()
    render_kline(hist, display_name)


def render_kline(df: pd.DataFrame, title: str):
    """渲染专业 K 线图 + 成交量 + 技术指标"""
    if df is None or df.empty:
        st.info("暂无图表数据")
        return
    mobile_mode = _is_mobile_request()

    # 计算技术指标
    df = df.copy()
    df["ma5"]  = df["close"].rolling(5).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()

    # 布林带
    df["bb_mid"]   = df["close"].rolling(20).mean()
    df["bb_std"]   = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]

    # 成交量颜色
    colors = ["#ff6257" if c >= o else "#38f28b"
              for c, o in zip(df["close"], df["open"])]

    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.72, 0.28],
    )

    # ── K 线 ──
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"], high=df["high"],
        low=df["low"],   close=df["close"],
        increasing=dict(line=dict(color="#ff6257"), fillcolor="#ff6257"),
        decreasing=dict(line=dict(color="#38f28b"), fillcolor="#38f28b"),
        name="K线",
        showlegend=False,
    ), row=1, col=1)

    # ── 均线 ──
    for ma, color, name in [
        ("ma5",  "#F39C12", "MA5"),
        ("ma20", "#49c6ff", "MA20"),
        ("ma60", "#8f7cff", "MA60"),
    ]:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[ma],
            mode="lines",
            line=dict(color=color, width=1.2),
            name=name,
            opacity=0.9,
        ), row=1, col=1)

    # ── 布林带 ──
    fig.add_trace(go.Scatter(
        x=df.index, y=df["bb_upper"],
        mode="lines", line=dict(color="rgba(180,198,220,0.45)", width=0.9, dash="dot"),
        name="BB上轨", showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["bb_lower"],
        mode="lines", line=dict(color="rgba(180,198,220,0.45)", width=0.9, dash="dot"),
        fill="tonexty", fillcolor="rgba(73,198,255,0.06)",
        name="BB下轨", showlegend=False,
    ), row=1, col=1)

    # ── 成交量 ──
    fig.add_trace(go.Bar(
        x=df.index, y=df["volume"],
        marker_color=colors,
        name="成交量",
        showlegend=False,
        opacity=0.8,
    ), row=2, col=1)

    # ── 布局 ──
    # 最新价格
    latest = df["close"].iloc[-1]
    prev   = df["close"].iloc[-2] if len(df) > 1 else latest
    chg    = (latest - prev) / prev * 100 if prev else 0
    sign   = "▲" if chg >= 0 else "▼"
    color  = "#ff6257" if chg >= 0 else "#38f28b"

    fig.update_layout(
        title=dict(
            text=f"{title}　<span style='color:{color};font-size:14px'>{sign} {abs(chg):.2f}%　{latest:.2f}</span>",
            font=dict(size=16, color="#edf4ff"),
        ),
        height=440 if mobile_mode else 560,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(
            orientation="h", x=0, y=1.02,
            font=dict(size=11, color="#dfe9f8"),
            bgcolor="rgba(10,16,28,0.72)",
            bordercolor="rgba(110,170,255,0.2)",
            borderwidth=1,
        ),
        paper_bgcolor="rgba(6,9,14,0.96)",
        plot_bgcolor="#07111b",
        hovermode="x unified",
        font=dict(color="#dfe9f8"),
    )

    fig.update_xaxes(
        gridcolor="rgba(73,198,255,0.08)", gridwidth=0.6,
        showspikes=True, spikecolor="rgba(123,199,255,0.45)", spikethickness=1,
        tickfont=dict(color="#8ea3bd"),
        # 跳过周末和节假日，防止 zoom 到空白区间时 K 线消失
        rangebreaks=[dict(bounds=["sat", "mon"])],
        type="date",
    )
    fig.update_yaxes(
        gridcolor="rgba(73,198,255,0.08)", gridwidth=0.6,
        showspikes=True, spikecolor="rgba(123,199,255,0.45)",
        tickfont=dict(color="#8ea3bd"),
        autorange=True,
        fixedrange=False,
    )
    fig.update_yaxes(
        title_text="价格", title_font=dict(color="#8ea3bd"),
        row=1, col=1,
    )
    fig.update_yaxes(
        title_text="成交量", title_font=dict(color="#8ea3bd"),
        # 成交量 y 轴独立，不跟价格联动
        matches=None,
        row=2, col=1,
    )

    fig.update_layout(dragmode="zoom" if mobile_mode else "pan")
    st.plotly_chart(
        fig,
        width='stretch',
        config={
            "scrollZoom": True,
            "doubleClick": "reset",
            "displayModeBar": mobile_mode,
            "modeBarButtonsToAdd": ["zoom2d", "pan2d", "resetScale2d"],
            "responsive": True,
        },
    )


def render_metrics_row(df: pd.DataFrame, name_col: str, price_col: str, pct_col: str, n_cols: int = 3, sparklines: dict = None, detail_type: str = "", symbol_col: str = "代码"):
    """在多列中展示指标卡片，sparklines 为 {名称: [close prices]} 的可选字典"""
    if df is None or df.empty:
        st.info("数据加载中…")
        return
    actual_pct_col = get_pct_col(df, pct_col)
    cols = st.columns(min(n_cols, len(df)))
    for i, (_, row) in enumerate(df.iterrows()):
        with cols[i % n_cols]:
            try:
                pct = float(row[actual_pct_col]) if actual_pct_col else 0
                delta_str = f"{'+' if pct >= 0 else ''}{pct:.2f}%"
                direction = "up" if pct > 0 else ("down" if pct < 0 else "flat")
            except Exception:
                pct = 0
                delta_str = str(row.get(actual_pct_col or pct_col, ""))
                direction = "flat"

            val_class = "metric-up" if direction == "up" else ("metric-down" if direction == "down" else "metric-flat")
            raw_label = str(row[name_col])
            label = html_lib.escape(raw_label)
            value = html_lib.escape(str(row[price_col]))
            delta = html_lib.escape(delta_str)

            val_len = len(value.replace(",", "").replace(".", ""))
            if val_len <= 5:
                font_size = "1.75rem"
            elif val_len <= 7:
                font_size = "1.45rem"
            elif val_len <= 9:
                font_size = "1.15rem"
            else:
                font_size = "0.95rem"

            spark_html = ""
            if sparklines:
                prices = sparklines.get(str(row[name_col]), [])
                spark_html = make_sparkline_svg(prices, direction != "down")

            detail_symbol = str(row.get(symbol_col, "")).strip() if symbol_col else ""
            if not detail_symbol and detail_type == "cn_future":
                detail_symbol = raw_label
            can_open = bool(detail_type and detail_symbol)

            token_source = f"{detail_type}:{detail_symbol}"
            trigger_token = quote(token_source, safe="").replace("%", "_")
            trigger_id = f"__t{trigger_token}"
            card_id = f"card-{trigger_token}" if can_open else ""
            id_attr = f' id="{card_id}"' if card_id else ""
            card_class = "m-card clickable" if can_open else "m-card"

            if spark_html:
                card_html = (
                    f'<div class="{card_class}" style="position:relative;overflow:hidden;" data-trigger="{trigger_id}"{id_attr}>'
                    f'<div style="position:absolute;top:8px;right:8px;opacity:0.85;">{spark_html}</div>'
                    f'<div class="m-label">{label}</div>'
                    f'<div class="m-value {val_class}" style="font-size:{font_size}">{value}</div>'
                    f'<span class="m-badge {direction}">{delta}</span>'
                    f'</div>'
                )
            else:
                card_html = (
                    f'<div class="{card_class}" data-trigger="{trigger_id}"{id_attr}>'
                    f'<div class="m-label">{label}</div>'
                    f'<div class="m-value {val_class}" style="font-size:{font_size}">{value}</div>'
                    f'<span class="m-badge {direction}">{delta}</span>'
                    f'</div>'
                )
            st.markdown(card_html, unsafe_allow_html=True)

            # 隐藏触发按钮（绝对定位移出屏幕，保留 JS 可点击性）
            if can_open:
                if st.button(trigger_id, key=f"trigger_{trigger_token}"):
                    st.session_state["selected_asset"] = {
                        "symbol": detail_symbol,
                        "name": raw_label,
                        "type": detail_type,
                    }
                    st.session_state["detail_request_id"] = st.session_state.get("detail_request_id", 0) + 1
                    st.rerun()


def render_watchlist_row_actions(df: pd.DataFrame, market_key: str, key_prefix: str):
    if df is None or df.empty:
        st.info("当前市场还没有自选资产。")
        return

    headers = st.columns([1.2, 1.1, 1, 1, 1, 1.2])
    for col, label in zip(headers, ["名称", "代码", "现价", "涨跌幅", "更新时间", "✏ 操作"]):
        col.markdown(f"**{label}**")

    pending_key = f"{key_prefix}_pending_delete"
    current_watchlist = get_market_watchlists().get(market_key, [])
    meta = MARKET_CONFIG[market_key]

    for row_idx, (_, row) in enumerate(df.iterrows()):
        row_cols = st.columns([1.2, 1.1, 1, 1, 1, 1.2])
        symbol = str(row.get("代码", "")).strip()
        name = str(row.get("名称", symbol))
        pct_val = pd.to_numeric(row.get("涨跌幅"), errors="coerce")
        pct_text = ""
        if pd.notna(pct_val):
            pct_text = f"{pct_val:+.2f}%"

        with row_cols[0]:
            if st.button(name, key=f"{key_prefix}_name_{market_key}_{symbol}_{row_idx}", use_container_width=True):
                open_asset_detail(symbol, name, meta["asset_type"])
                st.rerun()
        row_cols[1].markdown(symbol or "-")
        row_cols[2].markdown(str(row.get("现价", "-")))
        row_cols[3].markdown(pct_text or str(row.get("涨跌幅", "-")))
        row_cols[4].markdown(str(row.get("更新时间", row.get("更新时", "-"))))

        with row_cols[5]:
            if st.session_state.get(pending_key) == symbol:
                confirm_cols = st.columns(2)
                with confirm_cols[0]:
                    if st.button("✏ 确认", key=f"{key_prefix}_confirm_{market_key}_{symbol}_{row_idx}", use_container_width=True):
                        updated = [item for item in current_watchlist if item != symbol]
                        watchlist_store.save_watchlist(market_key, updated)
                        st.session_state.pop(pending_key, None)
                        st.cache_data.clear()
                        st.rerun()
                with confirm_cols[1]:
                    if st.button("取消", key=f"{key_prefix}_cancel_{market_key}_{symbol}_{row_idx}", use_container_width=True):
                        st.session_state.pop(pending_key, None)
                        st.rerun()
            else:
                if st.button("✏ 删除", key=f"{key_prefix}_delete_{market_key}_{symbol}_{row_idx}", use_container_width=True):
                    st.session_state[pending_key] = symbol
                    st.rerun()

        st.markdown('<div style="height:1px;background:rgba(110,170,255,0.06);margin:0.12rem 0 0.18rem 0;"></div>', unsafe_allow_html=True)


def render_positions_row_actions(df: pd.DataFrame, positions: list[dict], key_prefix: str = "positions"):
    if df is None or df.empty:
        st.info("当前还没有持仓资产。")
        return

    headers = st.columns([1.0, 0.9, 1.1, 0.85, 0.85, 0.8, 0.8, 0.8, 0.95, 0.9, 1.4])
    for col, label in zip(headers, ["市场", "代码", "名称", "数量", "成本", "现价", "涨跌", "涨跌%", "持仓市值", "浮盈亏%", "✏ 操作"]):
        col.markdown(f"**{label}**")

    edit_key = f"{key_prefix}_editing_index"
    delete_key = f"{key_prefix}_pending_delete"

    for row_idx, row in df.iterrows():
        cols = st.columns([1.0, 0.9, 1.1, 0.85, 0.85, 0.8, 0.8, 0.8, 0.95, 0.9, 1.4])
        asset_index = int(row["index"])
        symbol = str(row["代码"])
        name = str(row["名称"])
        asset_type = str(row["asset_type"])

        cols[0].markdown(str(row["市场"]))
        cols[1].markdown(symbol)
        with cols[2]:
            if st.button(name, key=f"{key_prefix}_detail_{asset_index}_{row_idx}", use_container_width=True):
                open_asset_detail(symbol, name, asset_type)
                st.rerun()
        cols[3].markdown(f'{float(row["持仓数量"]):g}')
        cols[4].markdown(f'{float(row["持仓成本"]):g}')
        cols[5].markdown(str(row.get("现价", "")))
        cols[6].markdown(str(row.get("涨跌", "")))
        cols[7].markdown(f'{float(row["涨跌%"]):+.2f}%' if pd.notna(pd.to_numeric(row.get("涨跌%"), errors="coerce")) and str(row.get("涨跌%")) != "" else "")
        cols[8].markdown(str(row.get("持仓市值", "")))
        cols[9].markdown(f'{float(row["浮盈亏%"]):+.2f}%' if pd.notna(pd.to_numeric(row.get("浮盈亏%"), errors="coerce")) and str(row.get("浮盈亏%")) != "" else "")

        with cols[10]:
            if st.session_state.get(delete_key) == asset_index:
                action_cols = st.columns(2)
                with action_cols[0]:
                    if st.button("✏ 确认", key=f"{key_prefix}_confirm_delete_{asset_index}_{row_idx}", use_container_width=True):
                        watchlist_store.delete_position(asset_index)
                        st.session_state.pop(delete_key, None)
                        st.cache_data.clear()
                        st.rerun()
                with action_cols[1]:
                    if st.button("取消", key=f"{key_prefix}_cancel_delete_{asset_index}_{row_idx}", use_container_width=True):
                        st.session_state.pop(delete_key, None)
                        st.rerun()
            else:
                action_cols = st.columns(2)
                with action_cols[0]:
                    if st.button("✏ 修改", key=f"{key_prefix}_edit_{asset_index}_{row_idx}", use_container_width=True):
                        st.session_state[edit_key] = asset_index
                        st.rerun()
                with action_cols[1]:
                    if st.button("✏ 删除", key=f"{key_prefix}_delete_{asset_index}_{row_idx}", use_container_width=True):
                        st.session_state[delete_key] = asset_index
                        st.rerun()

        if st.session_state.get(edit_key) == asset_index:
            original = positions[asset_index]
            with st.container(border=True):
                st.caption(f"编辑持仓: {name} ({symbol})")
                edit_cols = st.columns(4)
                edit_cols[0].markdown("**市场**")
                edit_cols[0].markdown(str(original.get("market", "")) or "-")
                edit_cols[1].markdown("**代码**")
                edit_cols[1].markdown(str(original.get("symbol", "")) or "-")
                new_quantity = edit_cols[2].number_input("持仓数量", value=float(original.get("quantity", 0) or 0), step=1.0, key=f"{key_prefix}_qty_{asset_index}")
                new_cost = edit_cols[3].number_input("持仓成本", value=float(original.get("cost", 0) or 0), min_value=0.0, step=0.01, key=f"{key_prefix}_cost_{asset_index}")
                st.markdown("**名称**")
                st.markdown(str(original.get("name", "")) or "-")
                save_cols = st.columns(2)
                with save_cols[0]:
                    if st.button("保存修改", key=f"{key_prefix}_save_{asset_index}", use_container_width=True):
                        if float(new_quantity or 0) == 0:
                            watchlist_store.delete_position(asset_index)
                            st.session_state.pop(edit_key, None)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            watchlist_store.upsert_position(
                                {
                                    "market": str(original.get("market", "")),
                                    "symbol": str(original.get("symbol", "")),
                                    "name": get_canonical_asset_name(
                                        get_market_key_from_label(str(original.get("market", ""))),
                                        str(original.get("symbol", "")),
                                        fallback_name=str(original.get("name", "")),
                                    ),
                                    "quantity": new_quantity,
                                    "cost": new_cost,
                                    "note": original.get("note", ""),
                                },
                                index=asset_index,
                            )
                            st.session_state.pop(edit_key, None)
                            st.cache_data.clear()
                            st.rerun()
                with save_cols[1]:
                    if st.button("取消修改", key=f"{key_prefix}_cancel_{asset_index}", use_container_width=True):
                        st.session_state.pop(edit_key, None)
                        st.rerun()

        st.markdown('<div style="height:1px;background:rgba(110,170,255,0.06);margin:0.12rem 0 0.18rem 0;"></div>', unsafe_allow_html=True)


def render_position_metric_cards(df: pd.DataFrame, key_prefix: str = "position_cards"):
    if df is None or df.empty:
        st.info("当前还没有持仓资产。")
        return
    cols = st.columns(min(3, len(df)))
    for i, (_, row) in enumerate(df.iterrows()):
        with cols[i % len(cols)]:
            try:
                pct = float(row["涨跌%"])
                delta_str = f"{pct:+.2f}%"
                direction = "up" if pct > 0 else ("down" if pct < 0 else "flat")
            except Exception:
                delta_str = str(row.get("涨跌%", ""))
                direction = "flat"
            value = html_lib.escape(str(row.get("现价", "")))
            label = html_lib.escape(str(row.get("名称", "")))
            row_token = str(row.get("index", i))
            trigger_token = quote(f'{row.get("asset_type","")}:{row.get("代码","")}:{row_token}', safe="").replace("%", "_")
            trigger_id = f"__t{trigger_token}"
            card_id = f"card-{trigger_token}"
            spark_prices = get_position_history(str(row.get("asset_type", "")), str(row.get("代码", "")))
            spark_html = make_sparkline_svg(pd.to_numeric(spark_prices["close"], errors="coerce").dropna().tolist()[-30:], direction != "down") if spark_prices is not None and not spark_prices.empty else ""
            card_html = (
                f'<div class="m-card clickable" data-trigger="{trigger_id}" id="{card_id}">'
                f'<div class="m-label">{label}</div>'
                f'<div class="m-value {"metric-up" if direction=="up" else "metric-down" if direction=="down" else "metric-flat"}" style="font-size:1.35rem">{value}</div>'
                f'<span class="m-badge {direction}">{html_lib.escape(delta_str)}</span>'
                f'{f"<div style=\"position:absolute;top:8px;right:8px;opacity:0.85;\">{spark_html}</div>" if spark_html else ""}'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button(trigger_id, key=f"{key_prefix}_{trigger_token}"):
                open_asset_detail(str(row.get("代码", "")), str(row.get("名称", "")), str(row.get("asset_type", "")))
                st.rerun()


def build_position_summary_cards(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    cost_total = pd.to_numeric(df.get("持仓成本USD"), errors="coerce").fillna(0)
    market_total = pd.to_numeric(df.get("持仓市值USD"), errors="coerce").fillna(0)
    pnl_total = pd.to_numeric(df.get("浮盈亏USD"), errors="coerce").fillna(0)
    win_rate = ((pd.to_numeric(df["浮盈亏"], errors="coerce").fillna(0) > 0).sum() / len(df) * 100) if len(df) else 0
    fx_note = "人民币资产已按 USD/CNY 折算"
    return [
        {"label": "持仓资产数", "value": f"{len(df)} 项", "note": "真实持仓资产", "color": "#7bc7ff"},
        {"label": "持仓成本", "value": f"${cost_total.sum():,.2f}", "note": fx_note, "color": "#f2f7ff"},
        {"label": "持仓市值", "value": f"${market_total.sum():,.2f}", "note": fx_note, "color": "#f2f7ff"},
        {"label": "浮盈/浮亏", "value": f"${pnl_total.sum():+,.2f}", "note": fx_note, "color": "#38f28b" if pnl_total.sum() >= 0 else "#ff6257"},
        {"label": "胜率", "value": f"{win_rate:.0f}%", "note": "盈利持仓占比", "color": "#7bc7ff"},
    ]


def summarize_watchlist_market_breadth(total_watchlist_df: pd.DataFrame) -> list[dict]:
    if total_watchlist_df is None or total_watchlist_df.empty:
        return []
    cards = []
    for market_label, group in total_watchlist_df.groupby("市场", sort=False):
        numeric = pd.to_numeric(group.get("涨跌幅%"), errors="coerce").dropna()
        if numeric.empty:
            cards.append({"label": market_label, "value": "--", "note": "暂无可用行情", "color": "#8ea3bd"})
            continue
        up_count = int((numeric > 0).sum())
        total = int(len(numeric))
        cards.append(
            {
                "label": market_label,
                "value": f"{numeric.mean():+.2f}%",
                "note": f"{up_count}/{total} 上涨",
                "color": "#38f28b" if numeric.mean() >= 0 else "#ff6257",
            }
        )
    return cards


def render_position_performance_table(df: pd.DataFrame, key_prefix: str = "position_perf"):
    if df is None or df.empty:
        st.info("当前还没有持仓资产。")
        return
    show_cols = ["市场", "代码", "名称", "今日", "一周", "一个月", "今年至今", "全年", "下一财报"]
    header = st.columns([1.0, 0.9, 1.2, 0.8, 0.8, 0.9, 0.95, 0.9, 1.0])
    for col, label in zip(header, show_cols):
        col.markdown(f"**{label}**")
    for row_idx, (_, row) in enumerate(df.iterrows()):
        cols = st.columns([1.0, 0.9, 1.2, 0.8, 0.8, 0.9, 0.95, 0.9, 1.0])
        cols[0].markdown(str(row.get("市场", "")))
        cols[1].markdown(str(row.get("代码", "")))
        with cols[2]:
            if st.button(str(row.get("名称", "")), key=f"{key_prefix}_detail_{row_idx}", use_container_width=True):
                open_asset_detail(str(row.get("代码", "")), str(row.get("名称", "")), str(row.get("asset_type", "")))
                st.rerun()
        for idx, col_name in enumerate(["今日", "一周", "一个月", "今年至今", "全年"], start=3):
            val = pd.to_numeric(row.get(col_name), errors="coerce")
            cols[idx].markdown(f"{float(val):+.2f}%" if pd.notna(val) else "")
        cols[8].markdown(str(row.get("下一财报", "")))


def render_position_indicator_table(df: pd.DataFrame, key_prefix: str = "position_indicator"):
    if df is None or df.empty:
        st.info("当前还没有持仓资产。")
        return
    show_cols = ["市场", "代码", "名称", "现价", "涨跌", "涨跌%", "成交量", "RSI", "下一财报"]
    header = st.columns([1.0, 0.9, 1.2, 0.85, 0.85, 0.85, 0.9, 0.7, 1.0])
    for col, label in zip(header, show_cols):
        col.markdown(f"**{label}**")
    for row_idx, (_, row) in enumerate(df.iterrows()):
        cols = st.columns([1.0, 0.9, 1.2, 0.85, 0.85, 0.85, 0.9, 0.7, 1.0])
        cols[0].markdown(str(row.get("市场", "")))
        cols[1].markdown(str(row.get("代码", "")))
        with cols[2]:
            if st.button(str(row.get("名称", "")), key=f"{key_prefix}_detail_{row_idx}", use_container_width=True):
                open_asset_detail(str(row.get("代码", "")), str(row.get("名称", "")), str(row.get("asset_type", "")))
                st.rerun()
        cols[3].markdown(str(row.get("现价", "")))
        cols[4].markdown(str(row.get("涨跌", "")))
        pct_val = pd.to_numeric(row.get("涨跌%"), errors="coerce")
        cols[5].markdown(f"{float(pct_val):+.2f}%" if pd.notna(pct_val) else "")
        cols[6].markdown(str(row.get("成交量", "")))
        rsi_val = pd.to_numeric(row.get("RSI"), errors="coerce")
        cols[7].markdown(f"{float(rsi_val):.1f}" if pd.notna(rsi_val) else "")
        cols[8].markdown(str(row.get("下一财报", "")))


def _move_list_item(items: list, index: int, target: int) -> list:
    if not items or index < 0 or index >= len(items):
        return items
    target = max(0, min(len(items) - 1, target))
    if index == target:
        return items
    updated = list(items)
    item = updated.pop(index)
    updated.insert(target, item)
    return updated


def handle_monitor_action(row: pd.Series, action: str, mode: str):
    if mode == "watchlist":
        market_key = str(row.get("market_key", "")).strip()
        symbol = str(row.get("代码", "")).strip()
        monitor_key = str(row.get("monitor_key", f"{market_key}:{symbol}")).strip()
        current = get_market_watchlists().get(market_key, [])
        global_order = watchlist_store.get_watchlist_monitor_order()
        full_df = build_watchlist_monitor_frame(get_market_watchlists())
        current_global_keys = full_df["monitor_key"].tolist() if not full_df.empty and "monitor_key" in full_df.columns else []
        if not current:
            return
        if action == "delete":
            updated_market = [item for item in current if item != symbol]
            updated_global = [item for item in (global_order or current_global_keys) if item != monitor_key]
        elif action in ("top", "up", "down"):
            working = list(global_order or current_global_keys)
            if monitor_key not in working:
                working.append(monitor_key)
            current_index = working.index(monitor_key)
            if action == "top":
                updated_global = _move_list_item(working, current_index, 0)
            elif action == "up":
                updated_global = _move_list_item(working, current_index, current_index - 1)
            else:
                updated_global = _move_list_item(working, current_index, current_index + 1)
            updated_market = current
        else:
            return
        watchlist_store.save_watchlist(market_key, updated_market)
        watchlist_store.save_watchlist_monitor_order(updated_global)
    elif mode == "position":
        current = get_positions()
        index = int(row.get("index", -1))
        if not current or index < 0 or index >= len(current):
            return
        if action == "delete":
            del current[index]
        elif action == "top":
            current = _move_list_item(current, index, 0)
        elif action == "up":
            current = _move_list_item(current, index, index - 1)
        elif action == "down":
            current = _move_list_item(current, index, index + 1)
        else:
            return
        watchlist_store.save_positions(current)
    st.cache_data.clear()


def render_asset_monitor_table(df: pd.DataFrame, columns: list[tuple[str, str]], key_prefix: str = "asset_monitor", mode: str = ""):
    if df is None or df.empty:
        st.info("当前暂无可展示的数据。")
        return

    sort_key_state = f"{key_prefix}_sort_field"
    sort_dir_state = f"{key_prefix}_sort_dir"
    sort_field = st.session_state.get(sort_key_state, "")
    sort_dir = st.session_state.get(sort_dir_state, "asc")

    if sort_field and sort_field in df.columns:
        sort_series = df[sort_field]
        numeric_series = pd.to_numeric(sort_series, errors="coerce")
        if numeric_series.notna().any():
            df = df.assign(_sort_value=numeric_series)
        else:
            df = df.assign(_sort_value=sort_series.astype(str))
        df = df.sort_values("_sort_value", ascending=(sort_dir == "asc"), na_position="last").drop(columns="_sort_value").reset_index(drop=True)

    widths = []
    for label, _ in columns:
        if label in ("市场", "代码"):
            widths.append(0.9)
        elif label == "名称":
            widths.append(1.2)
        elif label in ("成交量", "浮盈亏情况"):
            widths.append(1.0)
        else:
            widths.append(0.85)
    widths.append(1.35)

    header_cols = st.columns(widths)
    for col, (label, field) in zip(header_cols, columns):
        indicator = ""
        if sort_field == field:
            indicator = " ↑" if sort_dir == "asc" else " ↓"
        if col.button(f"{label}{indicator}", key=f"{key_prefix}_sort_{field}", use_container_width=True):
            if sort_field == field:
                if sort_dir == "asc":
                    st.session_state[sort_dir_state] = "desc"
                else:
                    st.session_state.pop(sort_key_state, None)
                    st.session_state.pop(sort_dir_state, None)
            else:
                st.session_state[sort_key_state] = field
                st.session_state[sort_dir_state] = "asc"
            st.rerun()
    header_cols[-1].markdown("**✏ 操作**")
    delete_confirm_key = f"{key_prefix}_delete_confirm"

    for row_idx, (_, row) in enumerate(df.iterrows()):
        row_cols = st.columns(widths)
        row_token = f'{mode}:{row.get("市场","")}:{row.get("代码","")}:{row.get("source_index", row.get("index", row_idx))}'
        for idx, (label, field) in enumerate(columns):
            value = row.get(field, "")
            if label == "名称":
                with row_cols[idx]:
                    if st.button(str(value), key=f"{key_prefix}_detail_{row_idx}_{field}", use_container_width=True):
                        open_asset_detail(str(row.get("asset_symbol", row.get("代码", ""))), str(row.get("asset_name", value)), str(row.get("asset_type", "")))
                        st.rerun()
                continue

            if label in ("涨跌%", "RSI"):
                numeric = pd.to_numeric(value, errors="coerce")
                if pd.notna(numeric):
                    if label == "涨跌%":
                        value = f"{float(numeric):+.2f}%"
                    else:
                        value = f"{float(numeric):.1f}"
            if label in ("涨跌", "涨跌%", "浮盈亏情况"):
                numeric = pd.to_numeric(row.get(field), errors="coerce")
                if label == "浮盈亏情况":
                    raw_text = str(value)
                    if raw_text.startswith("+"):
                        row_cols[idx].markdown(f'<span style="color:#38f28b;font-weight:600;">{html_lib.escape(raw_text)}</span>', unsafe_allow_html=True)
                        continue
                    if raw_text.startswith("-"):
                        row_cols[idx].markdown(f'<span style="color:#ff6257;font-weight:600;">{html_lib.escape(raw_text)}</span>', unsafe_allow_html=True)
                        continue
                elif pd.notna(numeric):
                    color = "#38f28b" if float(numeric) > 0 else "#ff6257" if float(numeric) < 0 else "#8ea3bd"
                    row_cols[idx].markdown(f'<span style="color:{color};font-weight:600;">{html_lib.escape(str(value))}</span>', unsafe_allow_html=True)
                    continue
            row_cols[idx].markdown(str(value))

        with row_cols[-1]:
            with st.popover("✏", use_container_width=True):
                if st.button("置顶", key=f"{key_prefix}_top_{row_idx}", use_container_width=True):
                    handle_monitor_action(row, "top", mode)
                    st.rerun()
                if st.button("上移", key=f"{key_prefix}_up_{row_idx}", use_container_width=True):
                    handle_monitor_action(row, "up", mode)
                    st.rerun()
                if st.button("下移", key=f"{key_prefix}_down_{row_idx}", use_container_width=True):
                    handle_monitor_action(row, "down", mode)
                    st.rerun()
                if st.session_state.get(delete_confirm_key) == row_token:
                    st.warning("确认删除这条记录？")
                    confirm_cols = st.columns(2)
                    with confirm_cols[0]:
                        if st.button("确认删除", key=f"{key_prefix}_confirm_delete_{row_idx}", use_container_width=True):
                            handle_monitor_action(row, "delete", mode)
                            st.session_state.pop(delete_confirm_key, None)
                            st.rerun()
                    with confirm_cols[1]:
                        if st.button("取消", key=f"{key_prefix}_cancel_delete_{row_idx}", use_container_width=True):
                            st.session_state.pop(delete_confirm_key, None)
                            st.rerun()
                else:
                    if st.button("删除", key=f"{key_prefix}_delete_{row_idx}", use_container_width=True):
                        st.session_state[delete_confirm_key] = row_token
                        st.rerun()

        st.markdown('<div style="height:1px;background:rgba(110,170,255,0.06);margin:0.12rem 0 0.18rem 0;"></div>', unsafe_allow_html=True)

def render_import_preview(mode: str):
    preview_key = f"{mode}_import_preview"
    if preview_key not in st.session_state:
        return

    title = "自选导入预览" if mode == "watchlist" else "持仓导入预览"
    st.markdown(f"**{title}**")
    preview_df = pd.DataFrame(st.session_state[preview_key])
    if preview_df.empty:
        st.info("AI 没有识别出可导入的资产。")
        return

    if mode == "watchlist":
        preview_df = preview_df.reindex(columns=["market", "symbol", "name"]).fillna("")
        edited = st.data_editor(
            preview_df,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "market": st.column_config.SelectboxColumn("市场", options=list(MARKET_LABEL_TO_KEY.keys()), required=True),
                "symbol": st.column_config.TextColumn("代码", required=True),
                "name": st.column_config.TextColumn("名称"),
            },
            key=f"{mode}_preview_editor",
            use_container_width=True,
        )
        confirm_label = "确认导入自选"
    else:
        preview_df = preview_df.reindex(columns=["market", "symbol", "name", "quantity", "cost"]).fillna("")
        edited = st.data_editor(
            preview_df,
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "market": st.column_config.SelectboxColumn("市场", options=list(MARKET_LABEL_TO_KEY.keys()), required=True),
                "symbol": st.column_config.TextColumn("代码", required=True),
                "name": st.column_config.TextColumn("名称"),
                "quantity": st.column_config.NumberColumn("持仓数量", min_value=0.0),
                "cost": st.column_config.NumberColumn("持仓成本", min_value=0.0),
            },
            key=f"{mode}_preview_editor",
            use_container_width=True,
        )
        confirm_label = "确认导入持仓"

    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button(confirm_label, key=f"{mode}_confirm_import", use_container_width=True):
            records = edited.to_dict("records")
            if mode == "watchlist":
                current = get_market_watchlists()
                grouped = {key: list(current.get(key, [])) for key in MARKET_CONFIG}
                for row in records:
                    market_label = str(row.get("market", "")).strip()
                    symbol = str(row.get("symbol", "")).strip()
                    if not market_label or not symbol:
                        continue
                    market_key = get_market_key_from_label(market_label)
                    grouped.setdefault(market_key, []).append(symbol)
                watchlist_store.save_watchlists(grouped)
            else:
                normalized_positions = []
                for row in records:
                    market_label = str(row.get("market", "")).strip()
                    symbol = str(row.get("symbol", "")).strip()
                    if not market_label or not symbol:
                        continue
                    normalized_positions.append(
                        {
                            "market": market_label,
                            "symbol": symbol,
                            "name": str(row.get("name", "")).strip(),
                            "quantity": row.get("quantity", 0),
                            "cost": row.get("cost", 0),
                            "note": "",
                        }
                    )
                watchlist_store.save_positions(get_positions() + normalized_positions)
            st.session_state.pop(preview_key, None)
            st.cache_data.clear()
            st.rerun()
    with action_cols[1]:
        if st.button("取消导入", key=f"{mode}_cancel_import", use_container_width=True):
            st.session_state.pop(preview_key, None)
            st.rerun()


def handle_image_import(mode: str, uploader_key: str, button_key: str):
    file = st.file_uploader(
        "上传截图",
        type=["png", "jpg", "jpeg", "webp"],
        key=uploader_key,
        help="上传交易软件截图，AI 会先识别并生成可编辑预览。",
    )
    if st.button("开始 AI 识别", key=button_key, use_container_width=True):
        if not file:
            st.warning("请先上传截图。")
            return
        if not config.CLAUDE_API_KEY:
            st.warning("当前未配置 Claude API Key，暂时无法识别截图。")
            return
        with st.spinner("AI 正在识别截图…"):
            try:
                items = recognize_import_from_image(file, mode)
            except Exception as exc:
                st.error(f"截图识别失败：{exc}")
                return
        st.session_state[f"{mode}_import_preview"] = items
        st.rerun()


# ════════════════════════════════════════════════════════════════════
#  侧边栏
# ════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-kicker">Global Macro Desk</div>
            <div class="sidebar-title">全球市场监控</div>
            <div class="sidebar-subtitle">把指数、商品、自选股和 AI 解读放在同一块交易看板里。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    st.divider()

    page = st.radio(
        "导航",
        ["🏠 市场总览", "⭐ 自选与持仓监控", "🧾 自选管理", "💼 持仓管理", "🤖 AI 早报", "US 美股", "CN A股", "📦 期货", "📊 K线图表"],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    # Tushare 配置状态
    if not config.TUSHARE_TOKEN:
        st.warning("⚠️ A股未配置\n\n请在 config.py 填入 Tushare Token")
        with st.expander("如何获取 Token?"):
            st.markdown("""
1. 前往 [tushare.pro](https://tushare.pro) 注册
2. 登录 → 个人中心 → 接口TOKEN
3. 复制粘贴到 `config.py` 的 `TUSHARE_TOKEN`
4. 重启应用即可
""")
    else:
        st.success("✅ Tushare 已连接" if tushare_ok else "❌ Tushare 连接失败\n\n请检查 Token 是否正确")

    st.divider()

    # 手动刷新
    if st.button("🔄 立即刷新", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"自动刷新间隔：{format_refresh_interval(config.REFRESH_INTERVAL)}")


ensure_page_autorefresh()

# ── 注入 JS：隐藏所有 __t 开头的触发按钮 ────────────────────────
import streamlit.components.v1 as _components
_components.html("""
<script>
(function() {
    return;
    function setup() {
        try {
            var doc = window.parent.document;

            // 1. 隐藏所有 __t 触发按钮
            doc.querySelectorAll('[id^="card-"]').forEach(function(card) {
                var triggerText = card.getAttribute('data-trigger') || ('__t' + card.id.slice(5));
                if (!triggerText) return;

            function findLocalTriggerButton(card, triggerText) {
                var node = card.closest('[data-testid="column"]') || card.parentElement;
                while (node) {
                    var btns = node.querySelectorAll('button');
                    for (var i = btns.length - 1; i >= 0; i--) {
                        var txt = (btns[i].innerText || btns[i].textContent || '').trim();
                        if (txt === triggerText) return btns[i];
                    }
                    node = node.parentElement;
                }
                return null;
            }

            // 2. 给 id="card-XXX" 的卡片绑定点击事件
            doc.querySelectorAll('[id^="card-"]').forEach(function(card) {
                card.style.cursor = 'pointer';
                card.onclick = function() {
                    var triggerText = card.getAttribute('data-trigger') || ('__t' + card.id.slice(5));
                    var btn = findLocalTriggerButton(card, triggerText);
                    if (btn) {
                        btn.click();
                        return;
                    }
                    var btns = doc.querySelectorAll('button');
                    for (var i = btns.length - 1; i >= 0; i--) {
                        if ((btns[i].innerText || btns[i].textContent || '').trim() === triggerText) {
                            btns[i].click();
                            return;
                        }
                    }
                };
            });
        } catch(e) {}
    }

    setup();
    setTimeout(setup, 150);
    setTimeout(setup, 500);
    var obs = new MutationObserver(setup);
    try { obs.observe(window.parent.document.body, {childList:true, subtree:true}); } catch(e) {}
})();
</script>
""", height=0)

# ── 资产详情弹窗触发（全局，所有页面均有效）──────────────────────
_components.html("""
<script>
(function() {
    function hideInternalDetailButtons() {
        try {
            var doc = window.parent.document;
            doc.querySelectorAll('button').forEach(function(btn) {
                var txt = (btn.innerText || btn.textContent || '').trim();
                if (!txt.startsWith('__t')) return;
                var wrap = btn.closest('[data-testid="stButton"]');
                if (!wrap) return;
                wrap.style.cssText =
                    'position:absolute!important;left:-9999px!important;top:auto!important;'
                    + 'width:1px!important;height:1px!important;overflow:hidden!important;';
            });
        } catch (e) {}
    }

    function bindCardToLocalButton() {
        try {
            var doc = window.parent.document;
            doc.querySelectorAll('[data-trigger]').forEach(function(el) {
                var triggerText = el.getAttribute('data-trigger');
                if (!triggerText) return;
                if (el.dataset.boundTrigger === triggerText) return;

                el.dataset.boundTrigger = triggerText;
                el.style.cursor = 'pointer';
                el.onclick = function() {
                    var node = el.closest('[data-testid="column"]') || el.parentElement;
                    while (node) {
                        var btns = node.querySelectorAll('button');
                        for (var i = btns.length - 1; i >= 0; i--) {
                            var txt = (btns[i].innerText || btns[i].textContent || '').trim();
                            if (txt === triggerText || txt === '查看详情') {
                                btns[i].click();
                                return;
                            }
                        }
                        node = node.parentElement;
                    }
                    var btns = doc.querySelectorAll('button');
                    for (var j = btns.length - 1; j >= 0; j--) {
                        var txt2 = (btns[j].innerText || btns[j].textContent || '').trim();
                        if (txt2 === triggerText) {
                            btns[j].click();
                            return;
                        }
                    }
                };
            });
        } catch (e) {}
    }

    hideInternalDetailButtons();
    bindCardToLocalButton();
    setTimeout(hideInternalDetailButtons, 100);
    setTimeout(bindCardToLocalButton, 100);
    setTimeout(hideInternalDetailButtons, 400);
    setTimeout(bindCardToLocalButton, 400);
    var obs = new MutationObserver(function() {
        hideInternalDetailButtons();
        bindCardToLocalButton();
    });
    try { obs.observe(window.parent.document.body, {childList:true, subtree:true}); } catch(e) {}
})();
</script>
""", height=0)

if st.session_state.get("detail_request_id", 0) > st.session_state.get("detail_shown_id", 0):
    asset = st.session_state.get("selected_asset") or {}
    sym = asset.get("symbol", "")
    name = asset.get("name", sym)
    asset_type = asset.get("type", "us_stock")
    if sym:
        st.session_state["detail_shown_id"] = st.session_state.get("detail_request_id", 0)
        show_asset_detail(sym, name, asset_type)

# ════════════════════════════════════════════════════════════════════
#  页面：市场总览
# ════════════════════════════════════════════════════════════════════
if page == "⭐ 自选与持仓监控":
    render_hero(
        "自选与持仓监控",
        "把自选资产与真实持仓拆成两个监控面板，分别查看关键行情指标和盈亏状态。",
        kicker="Unified Monitor",
    )
    watchlists = get_market_watchlists()
    watchlist_df = build_watchlist_monitor_frame(watchlists)
    positions = get_positions()
    position_df = build_positions_frame(positions)

    tab_watch, tab_position = st.tabs(["📋 自选监控", "💼 持仓监控"])

    with tab_watch:
        if watchlist_df.empty:
            st.info("当前自选为空，请先到“自选管理”添加或导入资产。")
        else:
            render_asset_monitor_table(
                watchlist_df[["市场", "代码", "名称", "现价", "涨跌", "涨跌%", "成交量", "RSI", "asset_type", "asset_symbol", "asset_name", "market_key", "source_index"]],
                columns=[
                    ("市场", "市场"),
                    ("代码", "代码"),
                    ("名称", "名称"),
                    ("现价", "现价"),
                    ("涨跌", "涨跌"),
                    ("涨跌%", "涨跌%"),
                    ("成交量", "成交量"),
                    ("RSI", "RSI"),
                ],
                key_prefix="watch_monitor",
                mode="watchlist",
            )

    with tab_position:
        if position_df.empty:
            st.info("当前还没有持仓资产。")
        else:
            render_status_strip(build_position_summary_cards(position_df), title="💼 持仓总览")
            position_monitor_df = position_df.copy()
            position_monitor_df["持仓成本监控"] = position_monitor_df.apply(
                lambda row: f'${float(row["持仓成本USD"]):,.2f}'
                if pd.notna(pd.to_numeric(row.get("持仓成本USD"), errors="coerce"))
                else "",
                axis=1,
            )
            position_monitor_df["浮盈亏情况"] = position_monitor_df.apply(
                lambda row: (
                    f'${float(row["浮盈亏USD"]):+,.2f} / {float(row["浮盈亏%"]):+.2f}%'
                    if pd.notna(pd.to_numeric(row.get("浮盈亏USD"), errors="coerce"))
                    and pd.notna(pd.to_numeric(row.get("浮盈亏%"), errors="coerce"))
                    else ""
                ),
                axis=1,
            )
            render_asset_monitor_table(
                position_monitor_df[["市场", "代码", "名称", "持仓成本监控", "现价", "涨跌%", "浮盈亏情况", "成交量", "RSI", "asset_type", "asset_symbol", "asset_name", "index"]],
                columns=[
                    ("市场", "市场"),
                    ("代码", "代码"),
                    ("名称", "名称"),
                    ("成本", "持仓成本监控"),
                    ("现价", "现价"),
                    ("涨跌%", "涨跌%"),
                    ("浮盈亏情况", "浮盈亏情况"),
                    ("成交量", "成交量"),
                    ("RSI", "RSI"),
                ],
                key_prefix="position_monitor",
                mode="position",
            )

elif page == "🧾 自选管理":
    render_hero(
        "自选管理",
        "统一管理股票和期货自选，支持手动维护，也支持上传截图后由 AI 批量识别，确认预览后再入库。",
        kicker="Watchlist Admin",
    )
    watchlists = get_market_watchlists()

    with panel("AI 批量导入自选"):
        handle_image_import("watchlist", "watchlist_image_upload", "watchlist_ai_import_btn")
        render_import_preview("watchlist")

    with panel("手动新增自选"):
        add_cols = st.columns([2.4, 1], vertical_alignment="bottom")
        if st_keyup is not None:
            with add_cols[0]:
                symbol_text = st_keyup(
                    "代码或名称",
                    value=st.session_state.get("manual_watch_symbols", ""),
                    placeholder="支持代码、名称、逗号批量输入",
                    key="manual_watch_symbols_keyup",
                    debounce=0,
                    label_visibility="collapsed",
                )
                st.session_state["manual_watch_symbols"] = symbol_text
        else:
            symbol_text = add_cols[0].text_input("代码或名称", placeholder="支持代码、名称、逗号批量输入", key="manual_watch_symbols", label_visibility="collapsed")
        add_cols[0].markdown('<div class="block-label">代码或名称</div>', unsafe_allow_html=True)
        if add_cols[1].button("添加到自选", key="manual_watch_add_btn", use_container_width=True):
            market_key, symbols = infer_market_for_manual_watch(symbol_text)
            if not market_key or not symbols:
                st.warning("请先输入至少一个代码。")
            else:
                existing_symbols = watchlists.get(market_key, [])
                merged_symbols = normalize_symbols_for_market(existing_symbols + symbols, market_key)
                new_count = max(len(merged_symbols) - len(normalize_symbols_for_market(existing_symbols, market_key)), 0)
                watchlist_store.save_watchlist(market_key, merged_symbols)
                st.session_state["manual_watch_add_feedback"] = f"已添加 {new_count} 项到 {MARKET_KEY_TO_LABEL.get(market_key, market_key)}：{', '.join(symbols)}"
                st.cache_data.clear()
                st.rerun()
        suggestions = search_all_asset_suggestions(symbol_text)
        if suggestions and "," not in str(symbol_text or "") and "\n" not in str(symbol_text or ""):
            st.markdown('<div class="block-label">匹配资产</div>', unsafe_allow_html=True)
            suggestion_cols = st.columns(2)
            for idx, item in enumerate(suggestions):
                raw_symbol = str(item.get("raw_symbol", "")).strip()
                full_symbol = str(item.get("symbol", "")).strip()
                item_market_key = str(item.get("market_key", "")).strip()
                market_tag = str(item.get("market", MARKET_KEY_TO_LABEL.get(item_market_key, ""))).strip()
                with suggestion_cols[idx % 2]:
                    title_text = str(item.get("name", full_symbol)).strip()
                    symbol_text_line = raw_symbol if item_market_key == "cn" and raw_symbol else full_symbol
                    if symbol_text_line != full_symbol and full_symbol:
                        symbol_text_line = f"{symbol_text_line} ({full_symbol})"
                    st.markdown(
                        f"""
                        <div class="suggestion-card">
                            <div class="suggestion-market">{html_lib.escape(market_tag)}</div>
                            <div class="suggestion-title">{html_lib.escape(title_text)}</div>
                            <div class="suggestion-symbol">{html_lib.escape(symbol_text_line)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("添加这项", key=f'manual_watch_suggest_{item_market_key}_{idx}', use_container_width=True):
                        existing_symbols = watchlists.get(item_market_key, [])
                        merged_symbols = normalize_symbols_for_market(existing_symbols + [item["symbol"]], item_market_key)
                        new_count = max(len(merged_symbols) - len(normalize_symbols_for_market(existing_symbols, item_market_key)), 0)
                        watchlist_store.save_watchlist(item_market_key, merged_symbols)
                        st.session_state["manual_watch_add_feedback"] = f'已添加 {new_count} 项到 {MARKET_KEY_TO_LABEL.get(item_market_key, item_market_key)}：{item["symbol"]}'
                        st.cache_data.clear()
                        st.rerun()
        feedback_text = st.session_state.pop("manual_watch_add_feedback", "")
        if feedback_text:
            st.success(feedback_text)

    for market_key in ["us", "cn", "intl_futures", "cn_futures"]:
        market_label = MARKET_KEY_TO_LABEL[market_key]
        with panel(f"{market_label} 自选"):
            symbols = watchlists.get(market_key, [])
            st.caption(f"当前共 {len(symbols)} 项")
            if not symbols:
                st.info("当前为空，可手动添加或上传截图导入。")
                continue
            market_df = build_watchlist_market_frame(market_key, symbols)
            if market_df.empty:
                st.warning("行情暂未获取到，但你仍可保留该市场自选。")
                fallback_name_col = "资产名称"
                fallback_code_col = "资产代码"
                fallback_df = pd.DataFrame(
                    {
                        fallback_name_col: symbols,
                        fallback_code_col: symbols,
                        "现价": [""] * len(symbols),
                        "涨跌幅": [""] * len(symbols),
                        "更新时间": [""] * len(symbols),
                    }
                )
                render_watchlist_row_actions(fallback_df, market_key, key_prefix=f"manage_{market_key}")
            else:
                display_cols = [c for c in ["资产名称", "资产代码", "现价", "涨跌幅%", "更新时间"] if c in market_df.columns]
                rename_df = market_df[display_cols].rename(columns={"资产名称": "名称", "资产代码": "代码", "涨跌幅%": "涨跌幅"})
                render_watchlist_row_actions(rename_df, market_key, key_prefix=f"manage_{market_key}")

elif page == "💼 持仓管理":
    render_hero(
        "持仓管理",
        "统一管理真实持仓，支持截图 AI 识别、导入前预览确认，以及逐行修改持仓数量和持仓成本。",
        kicker="Portfolio Focus",
    )

    with panel("AI 批量导入持仓"):
        handle_image_import("positions", "positions_image_upload", "positions_ai_import_btn")
        render_import_preview("positions")

    with panel("手动新增持仓"):
        add_cols = st.columns([2.0, 0.7, 0.7, 1.0], vertical_alignment="bottom")
        if st_keyup is not None:
            with add_cols[0]:
                position_text = st_keyup(
                    "代码或名称",
                    value=st.session_state.get("manual_position_symbols", ""),
                    placeholder="支持代码或名称，自动识别市场",
                    key="manual_position_symbols_keyup",
                    debounce=0,
                    label_visibility="collapsed",
                )
                st.session_state["manual_position_symbols"] = position_text
        else:
            position_text = add_cols[0].text_input(
                "代码或名称",
                placeholder="支持代码或名称，自动识别市场",
                key="manual_position_symbols",
                label_visibility="collapsed",
            )
        add_cols[0].markdown('<div class="block-label">代码或名称</div>', unsafe_allow_html=True)
        qty_value = add_cols[1].number_input("数量", min_value=0.0, step=1.0, key="manual_position_qty")
        cost_value = add_cols[2].number_input("成本", min_value=0.0, step=0.01, key="manual_position_cost")
        selected_asset = infer_asset_for_manual_position(position_text)
        if add_cols[3].button("添加到持仓", key="manual_position_add_btn", use_container_width=True):
            if not selected_asset:
                st.warning("请先输入可识别的资产代码或名称。")
            else:
                add_manual_position_entry(selected_asset, qty_value, cost_value)

        pending_merge = st.session_state.get("manual_position_pending_merge")
        if pending_merge:
            pending_asset = dict(pending_merge.get("asset_item", {}) or {})
            pending_symbol = str(pending_asset.get("symbol", "")).strip()
            pending_name = str(pending_asset.get("name", pending_symbol)).strip() or pending_symbol
            existing_index = pending_merge.get("existing_index")
            existing_item = get_positions()[existing_index] if isinstance(existing_index, int) and 0 <= existing_index < len(get_positions()) else {}
            st.warning(
                f"持仓里已存在 {pending_name} ({pending_symbol})。是否要合并资产？"
            )
            confirm_cols = st.columns([1, 1, 1.2])
            if confirm_cols[0].button("合并资产", key="manual_position_merge_yes", use_container_width=True):
                _save_manual_position_entry(
                    pending_asset,
                    float(pending_merge.get("quantity", 0) or 0),
                    float(pending_merge.get("cost", 0) or 0),
                    merge_with_existing=True,
                )
            if confirm_cols[1].button("单独新增", key="manual_position_merge_no", use_container_width=True):
                _save_manual_position_entry(
                    pending_asset,
                    float(pending_merge.get("quantity", 0) or 0),
                    float(pending_merge.get("cost", 0) or 0),
                    merge_with_existing=False,
                )
            if confirm_cols[2].button("取消", key="manual_position_merge_cancel", use_container_width=True):
                st.session_state["manual_position_pending_merge"] = None
                st.rerun()
            if existing_item:
                st.caption(
                    f"现有仓位：数量 {float(existing_item.get('quantity', 0) or 0):g}，"
                    f"成本 {float(existing_item.get('cost', 0) or 0):g}"
                )

        position_suggestions = search_all_asset_suggestions(position_text)
        if position_suggestions and "," not in str(position_text or "") and "\n" not in str(position_text or ""):
            st.markdown('<div class="block-label">匹配资产</div>', unsafe_allow_html=True)
            suggestion_cols = st.columns(2)
            for idx, item in enumerate(position_suggestions):
                raw_symbol = str(item.get("raw_symbol", "")).strip()
                full_symbol = str(item.get("symbol", "")).strip()
                item_market_key = str(item.get("market_key", "")).strip()
                market_tag = str(item.get("market", MARKET_KEY_TO_LABEL.get(item_market_key, ""))).strip()
                with suggestion_cols[idx % 2]:
                    title_text = str(item.get("name", full_symbol)).strip()
                    symbol_text_line = raw_symbol if item_market_key == "cn" and raw_symbol else full_symbol
                    if symbol_text_line != full_symbol and full_symbol:
                        symbol_text_line = f"{symbol_text_line} ({full_symbol})"
                    st.markdown(
                        f"""
                        <div class="suggestion-card">
                            <div class="suggestion-market">{html_lib.escape(market_tag)}</div>
                            <div class="suggestion-title">{html_lib.escape(title_text)}</div>
                            <div class="suggestion-symbol">{html_lib.escape(symbol_text_line)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("添加这项", key=f'manual_position_suggest_{item_market_key}_{idx}', use_container_width=True):
                        add_manual_position_entry(item, qty_value, cost_value)

        feedback_text = st.session_state.pop("manual_position_add_feedback", "")
        if feedback_text:
            st.success(feedback_text)

    positions = get_positions()
    position_df = build_positions_frame(positions)
    render_status_strip(build_position_summary_cards(position_df), title="💼 持仓总览")

    with panel("持仓资产表"):
        render_positions_row_actions(position_df, positions)

    with panel("持仓资产指标表"):
        render_position_indicator_table(position_df[["市场", "代码", "名称", "现价", "涨跌", "涨跌%", "成交量", "RSI", "下一财报", "asset_type"]], key_prefix="position_metric")

    with panel("持仓股近期表现"):
        render_position_performance_table(position_df[["市场", "代码", "名称", "今日", "一周", "一个月", "今年至今", "全年", "下一财报", "asset_type"]], key_prefix="position_perf")

elif page == "🏠 市场总览":
    render_hero(
        "全球金融市场总览",
        "一页查看美国指数、A股风向、大宗商品和核心自选股。设计上我把它收拢成更像晨会看板的结构：先看市场温度，再看关键资产，再下钻到明细表。",
        kicker="Opening Dashboard",
    )

    with st.spinner("加载美股指数…"):
        us_idx = load_us_index()
    with st.spinner("加载A股指数…"):
        cn_idx = load_cn_index(_tushare_ready=tushare_ok)
    with st.spinner("加载期货数据…"):
        fut_df = load_futures()
    with st.spinner("加载国内期货数据…"):
        cn_fut_df_dash = load_cn_futures()
    with st.spinner("加载自选股…"):
        us_df = load_us_data(tuple(get_us_watchlist()))
    positions = get_positions()
    position_df = build_positions_frame(positions)
    total_watchlist_df = build_total_watchlist_frame(get_market_watchlists())
    with st.spinner("加载全球市场快照…"):
        global_df = load_global_market_snapshot()
    with panel("🌐 全球市场追踪"):
        render_global_bubble_map(global_df)

    render_hot_news_panel()

    render_status_strip(build_position_summary_cards(position_df), title="💼 持仓总览")
    render_status_strip(summarize_watchlist_market_breadth(total_watchlist_df), title="📡 自选资产市场温度计")


    col_sec, col_earn = st.columns(2)
    with col_sec:
        with panel("🗂️ 美股板块热力图"):
            sector_df = load_sector_performance()
            sector_constituent_df = load_sector_constituents()
            render_sector_heatmap(sector_df, sector_constituent_df)
    with col_earn:
        with panel("📅 自选财报日历"):
            us_watch_union = sorted(set(get_us_watchlist()))
            earn_df = load_earnings_calendar(tuple(us_watch_union))
            render_earnings_calendar(earn_df)

    with panel("🇺🇸 美国指数脉搏"):
        us_idx_spark = _build_sparklines_from_df(us_idx, "名称", "代码") if not us_idx.empty else {}
        render_metrics_row(us_idx, "名称", "现价", "涨跌幅%", n_cols=3, sparklines=us_idx_spark, detail_type="us_index", symbol_col="代码")

    with panel("🇨🇳 A股风向"):
        if cn_idx is not None and not cn_idx.empty and cn_idx["现价"].iloc[0] != "—":
            cn_idx_spark = {
                str(row["名称"]): get_sparkline_prices_cn_index(str(row["代码"]))
                for _, row in cn_idx.iterrows() if "代码" in cn_idx.columns
            }
            render_metrics_row(cn_idx, "名称", "现价", "涨跌幅%", n_cols=3, sparklines=cn_idx_spark, detail_type="cn_index", symbol_col="代码")
        else:
            err = getattr(cn_stocks, "_last_error", None)
            if err:
                st.warning(f"A股数据获取失败：{err}")
            elif not tushare_ok:
                st.info("Tushare 未初始化，请确认 Token 配置正确后刷新页面。")
            else:
                render_metrics_row(cn_idx, "名称", "现价", "涨跌幅%", n_cols=3, detail_type="cn_index", symbol_col="代码")

    with panel("🌐 国际期货"):
        if not fut_df.empty:
            key_names = ["WTI原油", "黄金", "铜", "标普500期货", "纳指期货"]
            key_items = fut_df[fut_df["品种"].isin(key_names)].copy()
            # 获取 sparkline 数据（按品种名 → yfinance 代码）
            name_to_sym = dict(zip(fut_df["品种"], fut_df["代码"])) if "代码" in fut_df.columns else {}
            sparklines = {}
            for name in key_names:
                sym = name_to_sym.get(name)
                if sym:
                    sparklines[name] = get_sparkline_prices(sym, days=30)
            render_metrics_row(key_items, "品种", "现价", "涨跌幅%", n_cols=5, sparklines=sparklines, detail_type="intl_future", symbol_col="代码")
        else:
            st.info("当前未获取到国际期货数据")

    with panel("🇨🇳 国内期货"):
        if not cn_fut_df_dash.empty:
            key_cn_names = ["螺纹钢", "沪金", "沪铜", "沪深300", "原油"]
            key_cn = cn_fut_df_dash[cn_fut_df_dash["品种"].isin(key_cn_names)]
            cn_fut_spark = {
                name: get_sparkline_prices_ts(*CN_FUTURES_TS_CODE[name])
                for name in key_cn_names if name in CN_FUTURES_TS_CODE
            }
            render_metrics_row(key_cn, "品种", "现价", "涨跌幅%", n_cols=5, sparklines=cn_fut_spark, detail_type="cn_future", symbol_col="品种")
        else:
            st.info("当前未获取到国内期货数据")

    with panel("⭐ 核心持仓资产观察"):
        if not position_df.empty:
            render_position_metric_cards(position_df, key_prefix="overview_positions")
        else:
            st.info("当前还没有持仓资产")

    render_micro_status(
        [
            {"label": "A股数据", "value": "在线" if tushare_ok else "待连接", "color": "#1f8f63" if tushare_ok else "#9aa6b2"},
        ]
    )

    st.markdown(
        f"<div style='text-align:center;color:#3a4a5a;font-size:0.72rem;margin-top:1.5rem;'>"
        f"自动刷新 · 每 {format_refresh_interval(config.REFRESH_INTERVAL)} 一次 · "
        f"本地时间 {datetime.now().strftime('%H:%M:%S')}</div>",
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════
#  页面：AI 早报
# ════════════════════════════════════════════════════════════════════
elif page == "🤖 AI 早报":
    render_hero(
        "AI 市场早报",
        "把当前监控面板里的指数、商品和个股走势整理成晨会可读版本，适合盘前快速浏览。",
        kicker="Briefing Engine",
    )

    if not config.CLAUDE_API_KEY:
        st.error("请先配置 CLAUDE_API_KEY。")
        st.stop()

    from datetime import timezone, timedelta
    SGT = timezone(timedelta(hours=8))
    now_sgt = datetime.now(SGT)
    today_str = now_sgt.strftime("%Y-%m-%d")
    brief_dir = os.path.join(os.path.dirname(__file__), "briefs")
    os.makedirs(brief_dir, exist_ok=True)
    brief_path = os.path.join(brief_dir, f"{today_str}.md")
    github_token = getattr(config, "GITHUB_TOKEN", "") or ""

    brief_content = ""
    brief_time = ""

    # 1. 先读本地缓存（本次容器内已生成过）
    if os.path.exists(brief_path):
        with open(brief_path, "r", encoding="utf-8") as f:
            saved = f.read()
        lines = saved.splitlines()
        if lines and lines[0].startswith("<!-- generated:"):
            brief_time = lines[0].replace("<!-- generated:", "").replace("-->", "").strip()
            brief_content = "\n".join(lines[1:]).strip()
        else:
            brief_content = saved

    # 2. 本地没有 → 从 GitHub 读取（跨重启持久化）
    if not brief_content:
        brief_content, brief_time = github_store.read_brief(today_str)
        if brief_content:
            # 写入本地缓存，避免本次运行期间重复拉取
            with open(brief_path, "w", encoding="utf-8") as f:
                f.write(f"<!-- generated: {brief_time} -->\n{brief_content}")

    # 3. 仍无早报且已过 08:00 SGT → 自动生成
    if not brief_content and now_sgt.hour >= 8:
        with st.spinner("Claude 正在分析今日市场数据，生成早报…"):
            brief_content = ai_brief.generate_morning_brief()
            brief_time = now_sgt.strftime("%H:%M SGT")
            # 写本地
            with open(brief_path, "w", encoding="utf-8") as f:
                f.write(f"<!-- generated: {brief_time} -->\n{brief_content}")
            # 写 GitHub（持久化）
            github_store.write_brief(today_str, brief_content, brief_time, github_token)

    # 4. 08:00 前无今日早报 → 尝试展示昨日早报
    yesterday_str = ""
    yesterday_content = ""
    yesterday_time = ""
    if not brief_content and now_sgt.hour < 8:
        from datetime import timedelta as _td
        yesterday_str = (now_sgt - _td(days=1)).strftime("%Y-%m-%d")
        yesterday_path = os.path.join(brief_dir, f"{yesterday_str}.md")
        if os.path.exists(yesterday_path):
            with open(yesterday_path, "r", encoding="utf-8") as f:
                saved = f.read()
            lines = saved.splitlines()
            if lines and lines[0].startswith("<!-- generated:"):
                yesterday_time = lines[0].replace("<!-- generated:", "").replace("-->", "").strip()
                yesterday_content = "\n".join(lines[1:]).strip()
            else:
                yesterday_content = saved
        if not yesterday_content:
            yesterday_content, yesterday_time = github_store.read_brief(yesterday_str)

    if brief_content:
        with panel(f"今日早报 · {today_str}"):
            if brief_time:
                st.caption(f"生成时间：{brief_time}")
            st.markdown(brief_content)
            st.download_button(
                label="📥 下载早报（txt）",
                data=brief_content,
                file_name=f"早报_{today_str}.txt",
                mime="text/plain",
            )
    elif yesterday_content:
        with panel(f"昨日早报 · {yesterday_str}（今日早报将于 08:00 SGT 生成）"):
            if yesterday_time:
                st.caption(f"生成时间：{yesterday_time}")
            st.markdown(yesterday_content)
            st.download_button(
                label="📥 下载早报（txt）",
                data=yesterday_content,
                file_name=f"早报_{yesterday_str}.txt",
                mime="text/plain",
            )
    else:
        with panel("今日早报"):
            st.info(f"今日早报将在 **08:00 SGT** 自动生成。\n\n当前新加坡时间：{now_sgt.strftime('%H:%M')}")

    with panel("🔍 单标的快速分析"):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            ana_symbol = st.text_input("代码", "NVDA", key="ana_sym")
        with c2:
            ana_name = st.text_input("名称", "英伟达", key="ana_name")
        with c3:
            ana_pct = st.number_input("涨跌幅%", value=2.61, step=0.1, key="ana_pct")
        with c4:
            ana_market = st.selectbox("市场", ["美股", "A股", "期货"], key="ana_mkt")
            st.write("")
            ana_btn = st.button("分析原因", key="ana_go")

        if ana_btn and ana_symbol:
            with st.spinner("分析中…"):
                analysis = ai_brief.analyze_anomaly(ana_symbol, ana_name, ana_pct, ana_market)
            arrow = "📈" if ana_pct >= 0 else "📉"
            st.info(f"{arrow} **{ana_name} {ana_pct:+.2f}%**\n\n{analysis}")


# ════════════════════════════════════════════════════════════════════
#  页面：美股
# ════════════════════════════════════════════════════════════════════
elif page == "US 美股":
    render_hero(
        "美股行情",
        "聚焦自选股、强弱排序和单标的查询，让美股页面更像可操作的 watchlist 终端。",
        kicker="US Equities",
    )

    tab1, tab2 = st.tabs(["📋 自选股列表", "🔍 搜索查询"])

    with tab1:
        current_watchlist = get_us_watchlist()

        with panel("自选股管理"):
            st.info("美股自选的新增、逐行删除和 AI 截图导入，已经统一迁移到“自选管理”页。这里保留查看和分析。")
        with st.spinner("加载数据…"):
            us_df = load_us_data(tuple(current_watchlist))
        if not us_df.empty:
            with panel("自选股卡片"):
                us_stock_spark = _build_sparklines_from_df(us_df, "名称", "代码")
                render_metrics_row(us_df, "名称", "现价", "涨跌幅%", n_cols=3, sparklines=us_stock_spark, detail_type="us_stock", symbol_col="代码")
            with panel("强弱分布"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🔴 涨幅榜 Top 5")
                    top5 = us_df.nlargest(5, "涨跌幅%")[["名称", "代码", "现价", "涨跌幅%"]]
                    render_table(top5, detail_type="us_stock", symbol_col="代码", name_col="名称", clickable_cols=["名称"], key_prefix="us_top5")
                with col2:
                    st.subheader("🟢 跌幅榜 Top 5")
                    bot5 = us_df.nsmallest(5, "涨跌幅%")[["名称", "代码", "现价", "涨跌幅%"]]
                    render_table(bot5, detail_type="us_stock", symbol_col="代码", name_col="名称", clickable_cols=["名称"], key_prefix="us_bot5")
            with panel("全部自选股"):
                render_table(us_df, detail_type="us_stock", symbol_col="代码", name_col="名称", clickable_cols=["名称", "代码"], key_prefix="us_full_table")

    with tab2:
        with panel("单标的查询"):
            symbol_input = st.text_input("输入美股代码（如 AAPL、TSLA）", "AAPL").upper()
            period_map = {
                "1天": ("1d", "5m"),
                "1个月": ("1mo", "1d"),
                "3个月": ("3mo", "1d"),
                "6个月": ("6mo", "1d"),
                "1年": ("1y", "1d"),
                "2年": ("2y", "1d"),
                "5年": ("5y", "1d"),
                "全部": ("max", "1d"),
            }
            period_sel = st.selectbox("查看K线数据区间", list(period_map.keys()), index=6)

            if symbol_input:
                quote = us_stocks.get_quote([symbol_input])
                if not quote.empty:
                    row = quote.iloc[0]
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("现价", row.get("现价", "—"))
                    with c2: st.metric("涨跌幅", format_pct(row.get("涨跌幅%", 0)))
                    with c3: st.metric("涨跌额", row.get("涨跌额", "—"))

                period_value, interval_value = period_map[period_sel]
                hist = load_us_history(symbol_input, period_value, interval_value)
                render_kline(hist, f"{symbol_input} K线图")


# ════════════════════════════════════════════════════════════════════
#  页面：A股
# ════════════════════════════════════════════════════════════════════
elif page == "CN A股":
    render_hero(
        "A股行情",
        "把指数、北向资金和自选股集中呈现，适合早盘看方向、盘中盯风格切换。",
        kicker="China Equities",
    )

    if not tushare_ok:
        st.warning("请先在 config.py 中配置 Tushare Token，然后重启应用。")
        st.stop()

    with panel("🔀 北向与南向资金"):
        flow = cn_stocks.get_northbound_flow()
        flow_err = flow.get("error")
        if flow_err:
            st.warning(f"⚠️ 北向资金数据获取失败：{flow_err}")
        else:
            trade_date = flow.get("trade_date") or ""
            date_label = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}" if len(trade_date) == 8 else "—"
            nm = flow.get("north_money")   # 北向成交额（亿）
            hgt = flow.get("hgt")
            sgt = flow.get("sgt")

            # 北向：近30日成交额 sparkline
            north_hist_df = load_hsgt_history(days=30)
            north_hist = north_hist_df["north_money"].tolist() if not north_hist_df.empty else []
            north_spark = make_sparkline_svg(north_hist, up=True, width=140, height=52)

            # 南向：从 ggt_daily 取净买额
            ggt_latest = load_ggt_net_buy_latest()
            ggt_err = ggt_latest.get("error")
            south_net = ggt_latest.get("net_buy")
            south_buy = ggt_latest.get("buy_amount")
            south_sell = ggt_latest.get("sell_amount")
            south_date = ggt_latest.get("trade_date") or ""
            south_date_label = f"{south_date[:4]}-{south_date[4:6]}-{south_date[6:]}" if len(south_date) == 8 else "—"

            # 南向：近30日净买额柱状图（正绿负红）
            ggt_hist_df = load_ggt_net_buy_history(days=30)
            south_hist = ggt_hist_df["net_buy"].tolist() if not ggt_hist_df.empty else []
            south_bar = make_flow_bar_svg(south_hist, width=140, height=52)

            def _fmt_amt(v, unit="亿"):
                if v is None: return "—"
                sign = "+" if v >= 0 else ""
                color = "#38f28b" if v >= 0 else "#ff6257"
                return f'<span style="color:{color}">{sign}{v:.2f} {unit}</span>'

            def _north_card(nm, hgt, sgt, date_str, spark_svg):
                val_str = f"{nm:.2f}" if nm is not None else "暂无"
                color = "#7bc7ff"
                spark_block = f'<div style="flex-shrink:0;align-self:center;">{spark_svg}</div>' if spark_svg else ""
                return f"""
                <div style="background:rgba(6,12,22,0.6);border:1px solid rgba(110,170,255,0.10);
                    border-left:3px solid {color};border-radius:12px;padding:1.1rem 1.4rem;
                    display:flex;flex-direction:row;align-items:center;justify-content:space-between;gap:1rem;">
                    <div style="display:flex;flex-direction:column;gap:0.3rem;flex:1;min-width:0;">
                        <div style="font-size:0.78rem;color:#8ea3bd;letter-spacing:0.04em;">北向资金成交额</div>
                        <div style="font-size:1.8rem;font-weight:700;color:{color};">{val_str} <span style="font-size:0.9rem;font-weight:400;">亿</span></div>
                        <div style="margin-top:0.3rem;display:flex;flex-direction:column;gap:0.2rem;">
                            <div style="display:flex;justify-content:space-between;font-size:0.76rem;color:#8ea3bd;">
                                <span>沪股通</span>{_fmt_amt(hgt)}
                            </div>
                            <div style="display:flex;justify-content:space-between;font-size:0.76rem;color:#8ea3bd;">
                                <span>深股通</span>{_fmt_amt(sgt)}
                            </div>
                        </div>
                        <div style="font-size:0.72rem;color:#5a7a9a;margin-top:0.2rem;">数据日期：{date_str} &nbsp;·&nbsp; 近30日走势</div>
                    </div>
                    {spark_block}
                </div>"""

            def _south_card(net, buy, sell, date_str, bar_svg):
                if net is None:
                    net_color, sign, val_str = "#8ea3bd", "", "暂无"
                elif net >= 0:
                    net_color, sign, val_str = "#38f28b", "+", f"{net:.2f}"
                else:
                    net_color, sign, val_str = "#ff6257", "", f"{net:.2f}"
                bar_block = f'<div style="flex-shrink:0;align-self:center;">{bar_svg}</div>' if bar_svg else ""
                buy_fmt = f"{buy:.2f}" if buy is not None else "—"
                sell_fmt = f"{sell:.2f}" if sell is not None else "—"
                return f"""
                <div style="background:rgba(6,12,22,0.6);border:1px solid rgba(110,170,255,0.10);
                    border-left:3px solid {net_color};border-radius:12px;padding:1.1rem 1.4rem;
                    display:flex;flex-direction:row;align-items:center;justify-content:space-between;gap:1rem;">
                    <div style="display:flex;flex-direction:column;gap:0.3rem;flex:1;min-width:0;">
                        <div style="font-size:0.78rem;color:#8ea3bd;letter-spacing:0.04em;">南向资金净买额（港股通）</div>
                        <div style="font-size:1.8rem;font-weight:700;color:{net_color};">{sign}{val_str} <span style="font-size:0.9rem;font-weight:400;">亿</span></div>
                        <div style="margin-top:0.3rem;display:flex;flex-direction:column;gap:0.2rem;">
                            <div style="display:flex;justify-content:space-between;font-size:0.76rem;color:#8ea3bd;">
                                <span>买入</span><span style="color:#38f28b;">{buy_fmt} 亿</span>
                            </div>
                            <div style="display:flex;justify-content:space-between;font-size:0.76rem;color:#8ea3bd;">
                                <span>卖出</span><span style="color:#ff6257;">{sell_fmt} 亿</span>
                            </div>
                        </div>
                        <div style="font-size:0.72rem;color:#5a7a9a;margin-top:0.2rem;">数据日期：{date_str} &nbsp;·&nbsp; 近30日净买柱状图</div>
                    </div>
                    {bar_block}
                </div>"""

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(_north_card(nm, hgt, sgt, date_label, north_spark), unsafe_allow_html=True)
            with c2:
                if ggt_err:
                    st.warning(f"⚠️ 南向资金数据获取失败：{ggt_err}")
                else:
                    st.markdown(_south_card(south_net, south_buy, south_sell, south_date_label, south_bar), unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div style="
                    background: rgba(6,12,22,0.6);
                    border: 1px solid rgba(110,170,255,0.10);
                    border-left: 3px solid rgba(110,170,255,0.4);
                    border-radius: 12px;
                    padding: 1.1rem 1.4rem;
                    display: flex; flex-direction: column; gap: 0.35rem;
                ">
                    <div style="font-size:0.78rem;color:#8ea3bd;letter-spacing:0.04em;">查询时间</div>
                    <div style="font-size:2rem;font-weight:700;color:#7bc7ff;">{datetime.now().strftime("%H:%M:%S")}</div>
                    <div style="font-size:0.75rem;color:#5a7a9a;">最近交易日数据</div>
                </div>""", unsafe_allow_html=True)

    with panel("📊 主要指数"):
        with st.spinner("加载指数…"):
            cn_idx = load_cn_index(_tushare_ready=tushare_ok)
        err = getattr(cn_stocks, "_last_error", None)
        if err:
            st.warning(f"⚠️ 指数数据获取失败：{err}")
        if not cn_idx.empty:
            cols_show = [c for c in ["名称", "现价", "涨跌额", "涨跌幅%", "成交量(亿)"] if c in cn_idx.columns]
            render_table(cn_idx[cols_show + ["代码"]], detail_type="cn_index", symbol_col="代码", name_col="名称", clickable_cols=["名称"], key_prefix="cn_index")

    with panel("⭐ 自选股"):
        with st.spinner("加载自选股…"):
            cn_df = load_cn_watchlist_data(tuple(get_cn_watchlist()), _tushare_ready=tushare_ok)
        if not cn_df.empty:
            cols_show = [c for c in ["名称", "代码", "现价", "涨跌额", "涨跌幅%", "成交量(亿)"] if c in cn_df.columns]
            render_table(cn_df[cols_show], detail_type="cn_stock", symbol_col="代码", name_col="名称", clickable_cols=["名称", "代码"], key_prefix="cn_watch")


# ════════════════════════════════════════════════════════════════════
#  页面：期货
# ════════════════════════════════════════════════════════════════════
elif page == "📦 期货":
    render_hero(
        "期货行情",
        "国际大宗商品 + 国内主力合约，宏观风险偏好一屏掌握。",
        kicker="Commodities & Futures",
    )

    tab_intl, tab_cn = st.tabs(["🌐 国际期货", "🇨🇳 国内期货"])

    with tab_intl:
        with st.spinner("加载国际期货数据…"):
            fut_df = load_futures()

        if fut_df.empty:
            st.error("国际期货数据加载失败，请检查网络连接")
        else:
            with panel("国际期货实时行情"):
                cols_show = ["品种", "现价", "涨跌额", "涨跌幅%", "更新时间"]
                available = [c for c in cols_show if c in fut_df.columns]
                render_table(fut_df[["分类"] + available], detail_type="intl_future", symbol_col="代码", name_col="品种", clickable_cols=["品种"], key_prefix="intl_fut_table")

            with panel("涨跌幅对比"):
                chart_df = fut_df[["品种", "涨跌幅%"]].copy()
                chart_df["涨跌幅%"] = pd.to_numeric(chart_df["涨跌幅%"], errors="coerce")
                chart_df = chart_df.dropna(subset=["涨跌幅%"])
                if chart_df.empty:
                    st.info("当前暂无可用于绘制的国际期货涨跌幅数据")
                else:
                    chart_df["颜色"] = chart_df["涨跌幅%"].apply(lambda x: "涨" if x >= 0 else "跌")
                    fig = px.bar(
                        chart_df.sort_values("涨跌幅%"),
                        x="涨跌幅%", y="品种", orientation="h",
                        color="颜色",
                        color_discrete_map={"涨": "#38f28b", "跌": "#ff6257"},
                        height=max(300, len(chart_df) * 28),
                    )
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=20, b=0),
                        showlegend=False,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#dfe9f8"),
                    )
                    st.plotly_chart(fig, use_container_width=True)

    with tab_cn:
        with st.spinner("加载国内期货数据…"):
            cn_fut_df = load_cn_futures()

        if cn_fut_df.empty:
            st.warning("国内期货数据暂时无法获取，请确认已安装 akshare（`pip install akshare`）并检查网络连接。")
        else:
            with panel("国内期货实时行情"):
                cols_show = ["品种", "现价", "涨跌额", "涨跌幅%", "成交量(万手)", "更新时间"]
                available = [c for c in cols_show if c in cn_fut_df.columns]
                render_table(cn_fut_df[["分类"] + available], detail_type="cn_future", symbol_col="品种", name_col="品种", clickable_cols=["品种"], key_prefix="cn_fut_table")

            with panel("涨跌幅对比"):
                chart_df = cn_fut_df[["品种", "涨跌幅%"]].copy()
                chart_df["涨跌幅%"] = pd.to_numeric(chart_df["涨跌幅%"], errors="coerce")
                chart_df = chart_df.dropna(subset=["涨跌幅%"])
                if chart_df.empty:
                    st.info("当前暂无可用于绘制的国内期货涨跌幅数据")
                else:
                    chart_df["颜色"] = chart_df["涨跌幅%"].apply(lambda x: "涨" if x >= 0 else "跌")
                    fig = px.bar(
                        chart_df.sort_values("涨跌幅%"),
                        x="涨跌幅%", y="品种", orientation="h",
                        color="颜色",
                        color_discrete_map={"涨": "#38f28b", "跌": "#ff6257"},
                        height=max(300, len(chart_df) * 28),
                    )
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=20, b=0),
                        showlegend=False,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#dfe9f8"),
                    )
                    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════
#  页面：K线图表
# ════════════════════════════════════════════════════════════════════
elif page == "📊 K线图表":
    render_hero(
        "K线图表",
        "在更干净的分析界面里查看趋势、成交量和常用技术指标，适合单标的深看。",
        kicker="Chart Desk",
    )

    with panel("图表设置"):
        col1, col2, col3 = st.columns([2, 2, 1])
        market_options = ["美股", "A股", "A股指数", "期货（国际）", "期货（国内）"]
        cn_index_options = {name: code for code, name in cn_stocks.DEFAULT_CN_STOCKS["指数"]}
        intl_futures_options = {name: sym for sym, name in futures.get_all_symbols()}
        cn_futures_options = list(CN_FUTURES_TS_CODE.keys())
        with col1:
            market = st.selectbox("市场", market_options)
        with col2:
            if market == "美股":
                us_options = get_us_watchlist() or config.MY_US_WATCHLIST
                symbol = st.selectbox("标的", us_options)
                title = symbol
            elif market == "A股":
                cn_options = get_cn_watchlist() or config.MY_CN_WATCHLIST
                cn_option_labels = {
                    ts_code: next(
                        (
                            name
                            for group in cn_stocks.DEFAULT_CN_STOCKS.values()
                            for code, name in group
                            if code == ts_code
                        ),
                        ts_code,
                    )
                    for ts_code in cn_options
                }
                symbol = st.selectbox(
                    "标的",
                    cn_options,
                    format_func=lambda ts_code: f"{cn_option_labels.get(ts_code, ts_code)} ({ts_code})",
                )
                title = cn_option_labels.get(symbol, symbol)
            elif market == "A股指数":
                name_sel = st.selectbox("标的", list(cn_index_options.keys()))
                symbol = cn_index_options[name_sel]
                title = name_sel
            elif market == "期货（国际）":
                name_sel = st.selectbox("标的", list(intl_futures_options.keys()))
                symbol = intl_futures_options[name_sel]
                title = name_sel
            else:
                symbol = st.selectbox("标的", cn_futures_options)
                title = symbol
        with col3:
            period_map = {
                "1天": ("1d", "5m"),
                "1个月": ("1mo", "1d"),
                "3个月": ("3mo", "1d"),
                "6个月": ("6mo", "1d"),
                "1年": ("1y", "1d"),
                "2年": ("2y", "1d"),
                "5年": ("5y", "1d"),
                "全部": ("max", "1d"),
            }
            period_sel = st.selectbox("查看K线数据区间", list(period_map.keys()), index=6)

        with st.spinner("加载K线数据…"):
            period_value, interval_value = period_map[period_sel]
            if market == "美股":
                hist = load_us_history(symbol, period_value, interval_value)
            elif market in ("A股", "A股指数"):
                hist = load_cn_history(symbol)
            elif market == "期货（国际）":
                hist = load_futures_history(symbol, period_value, interval_value)
            else:
                hist = load_cn_futures_history(symbol)

        render_kline(hist, f"{title} — {period_sel}")

        if not hist.empty:
            with st.expander("查看原始数据"):
                render_table(hist.tail(30).reset_index(), pct_col="")


# ─── 页脚 ──────────────────────────────────────────────────────────
st.markdown("---")
st.caption("数据来源：Yahoo Finance（美股/期货）· Tushare Pro（A股） | 延迟约15分钟，仅供参考，不构成投资建议")
