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
from urllib.parse import quote
import time
import sys
import os

# 确保模块路径正确
sys.path.insert(0, os.path.dirname(__file__))

import config
from collectors import us_stocks, cn_stocks, futures, telegram_feed
from agents import morning_brief as ai_brief

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
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: rgba(73, 198, 255, 0.45);
        color: #ffffff;
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
    .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] > div {
        background: #0c1728 !important;
        color: #eaf2ff !important;
        border-color: rgba(110,170,255,0.14) !important;
    }
    .stMarkdown, .stCaption, .stText {
        color: inherit;
    }
    .news-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 0.85rem;
        margin-top: 0.35rem;
        margin-bottom: 0.3rem;
    }
    .news-card {
        background: linear-gradient(180deg, rgba(12, 19, 31, 0.98), rgba(8, 12, 20, 0.96));
        border: 1px solid rgba(110, 170, 255, 0.12);
        border-radius: 14px;
        padding: 0.95rem 1rem;
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.24);
        min-height: 140px;
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
    }
    .news-empty {
        padding: 0.9rem 1rem;
        border: 1px dashed rgba(110, 170, 255, 0.18);
        border-radius: 14px;
        color: var(--muted);
        background: rgba(9, 14, 22, 0.72);
    }
</style>
""", unsafe_allow_html=True)


# ─── 初始化 Tushare ───────────────────────────────────────────────
@st.cache_resource
def init_tushare():
    if config.TUSHARE_TOKEN:
        ok = cn_stocks.init_tushare(config.TUSHARE_TOKEN)
        return ok
    return False


tushare_ok = init_tushare()


# ─── 缓存数据获取（TTL=5分钟）────────────────────────────────────
@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_us_data():
    return us_stocks.get_quote(config.MY_US_WATCHLIST)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_us_index():
    syms = ["^GSPC", "^IXIC", "^DJI"]
    return us_stocks.get_quote(syms)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_cn_index():
    return cn_stocks.get_index_quote()

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_cn_stocks():
    return cn_stocks.get_stock_quote(config.MY_CN_WATCHLIST)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_futures():
    return futures.get_intl_futures_quote(config.MY_FUTURES_CATEGORIES)

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

    df = us_stocks.get_quote(list(symbol_map.keys()))
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


@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_telegram_hotspots():
    bot_token = getattr(config, "TELEGRAM_BOT_TOKEN", "") or ""
    chat_id   = getattr(config, "TELEGRAM_CHAT_ID",   "") or ""
    api_key   = getattr(config, "CLAUDE_API_KEY",     "") or ""
    return telegram_feed.get_recent_messages(
        bot_token,
        chat_id,
        limit=5,
        claude_api_key=api_key,
    )


def get_fragment_decorator(run_every: int | None = None):
    fragment_api = getattr(st, "fragment", None) or getattr(st, "experimental_fragment", None)
    if fragment_api is None:
        def passthrough(func):
            return func
        return passthrough
    return fragment_api(run_every=run_every)


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
    """对 DataFrame 应用样式"""
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


def render_status_strip(cards: list[dict]):
    html = ['<div class="status-strip">']
    for card in cards:
        html.append(
            f"""
            <div class="status-card">
                <div class="status-label">{card['label']}</div>
                <div class="status-value">{card['value']}</div>
                <div class="status-note">{card['note']}</div>
            </div>
            """
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_micro_status(items: list[dict]):
    html = ['<div class="micro-strip">']
    for item in items:
        html.append(
            f"""
            <div class="micro-pill">
                <span class="micro-dot" style="background:{item['color']};"></span>
                <span>{item['label']}：{item['value']}</span>
            </div>
            """
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


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

    rows_list = list(df.iterrows())
    n = len(rows_list)
    n_cols = min(n, 3)
    cols = st.columns(n_cols)

    for i, (_, row) in enumerate(rows_list):
        title = html_lib.escape(str(row.get("标题", "未命名消息")))
        body = html_lib.escape(str(row.get("内容", ""))).replace("\n", "<br>")
        source = html_lib.escape(str(row.get("来源", "Telegram")))
        date_str = html_lib.escape(str(row.get("日期", "")))
        time_str = html_lib.escape(str(row.get("时间", "")))
        with cols[i % n_cols]:
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
    open_panel("🗞 热点消息")

    new_df = load_telegram_hotspots()

    # 累积消息到 session_state，避免每次刷新丢失历史条目
    _key = "_tg_msg_cache"
    prev_df = st.session_state.get(_key, pd.DataFrame())
    if not new_df.empty:
        combined = pd.concat([new_df, prev_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["标题", "时间", "日期"])
        st.session_state[_key] = combined.head(20)
    display_df = st.session_state.get(_key, new_df).head(5)

    render_news_cards(display_df)
    close_panel()


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
        heatmap_df["size"] = pd.to_numeric(heatmap_df["市值(亿)"], errors="coerce").fillna(0)
    else:
        heatmap_df["size"] = 0
    heatmap_df["size"] = heatmap_df["size"].where(heatmap_df["size"] > 0, 1)

    heatmap_df["label"] = heatmap_df.apply(
        lambda row: f"{row[name_col]}<br>{format_pct(row[pct_col])}",
        axis=1,
    )

    fig = px.treemap(
        heatmap_df,
        path=[px.Constant(title), name_col],
        values="size",
        color=pct_col,
        color_continuous_scale=[
            [0.0, "#c9483b"],
            [0.45, "#f1ddd7"],
            [0.5, "#f3efe7"],
            [0.55, "#d9e8de"],
            [1.0, "#1f8f63"],
        ],
        color_continuous_midpoint=0,
        custom_data=[pct_col],
    )
    fig.update_traces(
        text=heatmap_df["label"],
        texttemplate="%{text}",
        textfont=dict(color="#12212f", size=16),
        marker=dict(line=dict(color="rgba(255,253,248,0.95)", width=2)),
        hovertemplate="<b>%{label}</b><br>涨跌幅: %{customdata[0]:+.2f}%<extra></extra>",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=8, b=0),
        height=320,
        paper_bgcolor="rgba(255,253,248,0.0)",
        plot_bgcolor="rgba(255,253,248,0.0)",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig, width='stretch')


def get_world_map_background_uri() -> str:
    image_path = os.path.join(os.path.dirname(__file__), "pic", "Globalmap.png")
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


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
    bubble_df["plot_x"] = bubble_df["名称"].map(lambda name: position_map.get(name, {"dot": (50, 50)})["dot"][0])
    bubble_df["plot_y"] = bubble_df["名称"].map(lambda name: position_map.get(name, {"dot": (50, 50)})["dot"][1])
    bubble_df["display_color"] = bubble_df["涨跌幅%"].apply(
        lambda value: "#38f28b" if value > 0 else "#ff6257" if value < 0 else "#ffffff"
    )

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
        pos = position_map.get(row["名称"], {"label": (row["plot_x"], row["plot_y"] - 2), "pct": (row["plot_x"], row["plot_y"] + 1)})
        fig.add_annotation(
            x=pos["label"][0],
            y=pos["label"][1],
            text=row["名称"],
            showarrow=False,
            font=dict(size=13, color=text_color, family="Arial Black"),
            xanchor="center",
            yanchor="middle",
            align="center",
        )
        fig.add_annotation(
            x=pos["pct"][0],
            y=pos["pct"][1],
            text=f"{row['涨跌幅%']:+.2f}%",
            showarrow=False,
            font=dict(size=13, color=text_color, family="Arial Black"),
            xanchor="center",
            yanchor="middle",
            align="center",
        )
    fig.update_layout(
        height=430,
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


def open_panel(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def close_panel():
    pass


def summarize_market(us_idx: pd.DataFrame, cn_idx: pd.DataFrame, fut_df: pd.DataFrame) -> list[dict]:
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
        {
            "label": "刷新节奏",
            "value": format_refresh_interval(config.REFRESH_INTERVAL),
            "note": f"本地时间 {datetime.now().strftime('%H:%M:%S')} · 手动刷新可立即更新",
        },
    ]
    return cards


def render_kline(df: pd.DataFrame, title: str):
    """渲染专业 K 线图 + 成交量 + 技术指标"""
    if df is None or df.empty:
        st.info("暂无图表数据")
        return

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
        height=560,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(
            orientation="h", x=0, y=1.02,
            font=dict(size=11),
            bgcolor="rgba(10,16,28,0.72)",
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
    )
    fig.update_yaxes(
        gridcolor="rgba(73,198,255,0.08)", gridwidth=0.6,
        showspikes=True, spikecolor="rgba(123,199,255,0.45)",
        tickfont=dict(color="#8ea3bd"),
    )
    fig.update_yaxes(title_text="价格", title_font=dict(color="#8ea3bd"), row=1, col=1)
    fig.update_yaxes(title_text="成交量", title_font=dict(color="#8ea3bd"), row=2, col=1)

    st.plotly_chart(fig, width='stretch')


def render_metrics_row(df: pd.DataFrame, name_col: str, price_col: str, pct_col: str, n_cols: int = 3):
    """在多列中展示指标卡片"""
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
            label = html_lib.escape(str(row[name_col]))
            value = html_lib.escape(str(row[price_col]))
            delta = html_lib.escape(delta_str)

            # 根据数字长度自动缩小字号，保持卡片高度一致
            val_len = len(value.replace(",", "").replace(".", ""))
            if val_len <= 5:
                font_size = "1.75rem"
            elif val_len <= 7:
                font_size = "1.45rem"
            elif val_len <= 9:
                font_size = "1.15rem"
            else:
                font_size = "0.95rem"

            st.markdown(
                f"""
                <div class="m-card">
                    <div class="m-label">{label}</div>
                    <div class="m-value {val_class}" style="font-size:{font_size}">{value}</div>
                    <span class="m-badge {direction}">{delta}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


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
        ["🏠 市场总览", "🤖 AI 早报", "🇺🇸 美股", "🇨🇳 A股", "📦 期货", "📊 K线图表"],
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


# ════════════════════════════════════════════════════════════════════
#  页面：市场总览
# ════════════════════════════════════════════════════════════════════
if page == "🏠 市场总览":
    render_hero(
        "全球金融市场总览",
        "一页查看美国指数、A股风向、大宗商品和核心自选股。设计上我把它收拢成更像晨会看板的结构：先看市场温度，再看关键资产，再下钻到明细表。",
        kicker="Opening Dashboard",
    )

    with st.spinner("加载美股指数…"):
        us_idx = load_us_index()
    with st.spinner("加载A股指数…"):
        cn_idx = load_cn_index()
    with st.spinner("加载期货数据…"):
        fut_df = load_futures()
    with st.spinner("加载自选股…"):
        us_df = load_us_data()
    with st.spinner("加载全球市场快照…"):
        global_df = load_global_market_snapshot()
    open_panel("🌐 全球市场追踪")
    render_global_bubble_map(global_df)
    close_panel()

    render_hot_news_panel()

    render_status_strip(summarize_market(us_idx, cn_idx, fut_df))

    if True:
        open_panel("🔥 美股热力表")
        render_market_heatmap(us_df, "美股自选")
        close_panel()

        open_panel("🇺🇸 美国指数脉搏")
        render_metrics_row(us_idx, "名称", "现价", "涨跌幅%", n_cols=3)
        close_panel()

        open_panel("🇨🇳 A股风向")
        render_metrics_row(cn_idx, "名称", "现价", "涨跌幅%", n_cols=3)
        close_panel()

        open_panel("📦 大宗商品与风险偏好")
        if not fut_df.empty:
            key_items = fut_df[fut_df["品种"].isin(["WTI原油", "黄金", "铜", "标普500期货", "纳指期货"])]
            render_metrics_row(key_items, "品种", "现价", "涨跌幅%", n_cols=5)
        else:
            st.info("当前未获取到期货数据")
        close_panel()

    open_panel("⭐ 核心自选股观察")
    if not us_df.empty:
        display_cols = ["名称", "现价", "涨跌额", "涨跌幅%", "更新时间"]
        available = [c for c in display_cols if c in us_df.columns]
        st.dataframe(
            style_table(us_df[available]),
            width='stretch',
            hide_index=True,
            height=340,
        )
    else:
        st.info("当前未获取到美股自选数据")
    close_panel()

    render_micro_status(
        [
            {"label": "A股数据", "value": "在线" if tushare_ok else "待连接", "color": "#1f8f63" if tushare_ok else "#9aa6b2"},
            {"label": "刷新频率", "value": format_refresh_interval(config.REFRESH_INTERVAL), "color": "#17324a"},
        ]
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

    # 读取已保存的今日早报
    brief_content = ""
    brief_time = ""
    if os.path.exists(brief_path):
        with open(brief_path, "r", encoding="utf-8") as f:
            saved = f.read()
        # 第一行存生成时间，格式：<!-- generated: HH:MM SGT -->
        lines = saved.splitlines()
        if lines and lines[0].startswith("<!-- generated:"):
            brief_time = lines[0].replace("<!-- generated:", "").replace("-->", "").strip()
            brief_content = "\n".join(lines[1:]).strip()
        else:
            brief_content = saved

    # 今日早报不存在且已过 08:00 SGT → 自动生成
    if not brief_content and now_sgt.hour >= 8:
        with st.spinner("Claude 正在分析今日市场数据，生成早报…"):
            brief_content = ai_brief.generate_morning_brief()
            brief_time = now_sgt.strftime("%H:%M SGT")
            with open(brief_path, "w", encoding="utf-8") as f:
                f.write(f"<!-- generated: {brief_time} -->\n{brief_content}")

    if brief_content:
        open_panel(f"今日早报 · {today_str}")
        if brief_time:
            st.caption(f"生成时间：{brief_time}")
        st.markdown(brief_content)
        st.download_button(
            label="📥 下载早报（txt）",
            data=brief_content,
            file_name=f"早报_{today_str}.txt",
            mime="text/plain",
        )
        close_panel()
    else:
        open_panel("今日早报")
        st.info(f"今日早报将在 **08:00 SGT** 自动生成。\n\n当前新加坡时间：{now_sgt.strftime('%H:%M')}")
        close_panel()

    open_panel("🔍 单标的快速分析")
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
    close_panel()


# ════════════════════════════════════════════════════════════════════
#  页面：美股
# ════════════════════════════════════════════════════════════════════
elif page == "🇺🇸 美股":
    render_hero(
        "美股行情",
        "聚焦自选股、强弱排序和单标的查询，让美股页面更像可操作的 watchlist 终端。",
        kicker="US Equities",
    )

    tab1, tab2 = st.tabs(["📋 自选股列表", "🔍 搜索查询"])

    with tab1:
        with st.spinner("加载数据…"):
            us_df = load_us_data()
        if not us_df.empty:
            # 涨跌榜
            open_panel("强弱分布")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🔴 涨幅榜 Top 5")
                top5 = us_df.nlargest(5, "涨跌幅%")[["名称", "现价", "涨跌幅%"]]
                st.dataframe(style_table(top5), hide_index=True, width='stretch')
            with col2:
                st.subheader("🟢 跌幅榜 Top 5")
                bot5 = us_df.nsmallest(5, "涨跌幅%")[["名称", "现价", "涨跌幅%"]]
                st.dataframe(style_table(bot5), hide_index=True, width='stretch')
            close_panel()
            open_panel("全部自选股")
            st.dataframe(style_table(us_df), width='stretch', hide_index=True)
            close_panel()

    with tab2:
        open_panel("单标的查询")
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
        period_sel = st.selectbox("查看区间", list(period_map.keys()), index=5)

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
        close_panel()


# ════════════════════════════════════════════════════════════════════
#  页面：A股
# ════════════════════════════════════════════════════════════════════
elif page == "🇨🇳 A股":
    render_hero(
        "A股行情",
        "把指数、北向资金和自选股集中呈现，适合早盘看方向、盘中盯风格切换。",
        kicker="China Equities",
    )

    if not tushare_ok:
        st.warning("请先在 config.py 中配置 Tushare Token，然后重启应用。")
        st.stop()

    open_panel("北向与南向资金")
    flow = cn_stocks.get_northbound_flow()
    c1, c2, c3 = st.columns(3)
    with c1:
        nm = flow.get("north_money")
        st.metric("北向资金净流入(亿)", f"{nm:+.2f}" if nm is not None else "暂无")
    with c2:
        sm = flow.get("south_money")
        st.metric("南向资金净流入(亿)", f"{sm:+.2f}" if sm is not None else "暂无")
    with c3:
        st.metric("更新时间", datetime.now().strftime("%H:%M:%S"))
    close_panel()

    open_panel("📊 主要指数")
    with st.spinner("加载指数…"):
        cn_idx = load_cn_index()
    if not cn_idx.empty:
        cols_show = [c for c in ["名称", "现价", "涨跌额", "涨跌幅%", "成交量(亿)"] if c in cn_idx.columns]
        st.dataframe(style_table(cn_idx[cols_show], pct_col="涨跌幅%"),
                     width='stretch', hide_index=True)
    close_panel()

    open_panel("⭐ 自选股")
    with st.spinner("加载自选股…"):
        cn_df = load_cn_stocks()
    if not cn_df.empty:
        cols_show = [c for c in ["名称", "代码", "现价", "涨跌额", "涨跌幅%", "成交量(亿)"] if c in cn_df.columns]
        st.dataframe(style_table(cn_df[cols_show], pct_col="涨跌幅%"),
                     width='stretch', hide_index=True)
    close_panel()


# ════════════════════════════════════════════════════════════════════
#  页面：期货
# ════════════════════════════════════════════════════════════════════
elif page == "📦 期货":
    render_hero(
        "期货行情",
        "把能源、贵金属、工业金属和股指期货放进一个宏观风险偏好面板里。",
        kicker="Commodities & Futures",
    )

    with st.spinner("加载期货数据…"):
        fut_df = load_futures()

    if fut_df.empty:
        st.error("期货数据加载失败，请检查网络连接")
    else:
        # 按分类展示
        for cat in fut_df["分类"].unique():
            open_panel(cat)
            sub = fut_df[fut_df["分类"] == cat].copy()
            cols_show = ["品种", "现价", "涨跌额", "涨跌幅%", "更新时间"]
            available = [c for c in cols_show if c in sub.columns]
            st.dataframe(
                style_table(sub[available]),
                width='stretch',
                hide_index=True,
            )
            close_panel()

        # 期货涨跌条形图
        open_panel("涨跌幅对比")
        chart_df = fut_df[["品种", "涨跌幅%"]].copy()
        chart_df["颜色"] = chart_df["涨跌幅%"].apply(lambda x: "涨" if float(x) >= 0 else "跌")
        fig = px.bar(
            chart_df.sort_values("涨跌幅%"),
            x="涨跌幅%", y="品种", orientation="h",
            color="颜色",
            color_discrete_map={"涨": "#27AE60", "跌": "#E74C3C"},
            height=max(300, len(chart_df) * 28),
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=False,
            paper_bgcolor="rgba(255,253,248,0.92)",
            plot_bgcolor="#fffaf2",
            font=dict(color="#12212f"),
        )
        st.plotly_chart(fig, width='stretch')
        close_panel()


# ════════════════════════════════════════════════════════════════════
#  页面：K线图表
# ════════════════════════════════════════════════════════════════════
elif page == "📊 K线图表":
    render_hero(
        "K线图表",
        "在更干净的分析界面里查看趋势、成交量和常用技术指标，适合单标的深看。",
        kicker="Chart Desk",
    )

    open_panel("图表设置")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        market = st.selectbox("市场", ["美股", "期货（国际）"])
    with col2:
        if market == "美股":
            symbol = st.selectbox("标的", config.MY_US_WATCHLIST)
        else:
            fut_options = {name: sym for sym, name in futures.get_all_symbols()}
            name_sel = st.selectbox("标的", list(fut_options.keys()))
            symbol = fut_options[name_sel]
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
        period_sel = st.selectbox("查看区间", list(period_map.keys()), index=5)

    with st.spinner("加载K线数据…"):
        period_value, interval_value = period_map[period_sel]
        if market == "美股":
            hist = load_us_history(symbol, period_value, interval_value)
            title = symbol
        else:
            hist = load_futures_history(symbol, period_value, interval_value)
            title = name_sel if market == "期货（国际）" else symbol

    render_kline(hist, f"{title} — {period_sel}")

    if not hist.empty:
        with st.expander("查看原始数据"):
            st.dataframe(hist.tail(30), width='stretch')
    close_panel()


# ─── 页脚 ──────────────────────────────────────────────────────────
st.markdown("---")
st.caption("数据来源：Yahoo Finance（美股/期货）· Tushare Pro（A股） | 延迟约15分钟，仅供参考，不构成投资建议")
