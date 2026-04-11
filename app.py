"""
全球金融市场监控平台 - 主应用
运行方式: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
import sys
import os

# 确保模块路径正确
sys.path.insert(0, os.path.dirname(__file__))

import config
from collectors import us_stocks, cn_stocks, futures
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
    .metric-up   { color: #E74C3C; font-weight: bold; }
    .metric-down { color: #27AE60; font-weight: bold; }
    .metric-flat { color: #7F8C8D; }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2C3E50;
        padding: 4px 0;
        border-bottom: 2px solid #3498DB;
        margin-bottom: 8px;
    }
    .stDataFrame thead th { background-color: #2C3E50 !important; color: white !important; }
    div[data-testid="metric-container"] { background: #F8F9FA; border-radius: 8px; padding: 8px; }
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
def load_us_history(symbol, period):
    return us_stocks.get_history(symbol, period=period)

@st.cache_data(ttl=config.REFRESH_INTERVAL)
def load_futures_history(symbol, period):
    return futures.get_futures_history(symbol, period=period)


# ─── 工具函数 ─────────────────────────────────────────────────────
def color_change(val):
    """给涨跌幅列上色"""
    try:
        v = float(val)
        if v > 0:
            return "color: #E74C3C; font-weight: bold"
        elif v < 0:
            return "color: #27AE60; font-weight: bold"
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


def style_table(df, pct_col="涨跌幅%"):
    """对 DataFrame 应用样式"""
    if df.empty:
        return df
    styled = df.style.map(color_change, subset=[pct_col]) \
                     .format({pct_col: format_pct}) \
                     .set_properties(**{"font-size": "13px"})
    return styled


def render_kline(df: pd.DataFrame, title: str):
    """渲染 K 线图 + 成交量"""
    if df is None or df.empty:
        st.info("暂无图表数据")
        return

    fig = go.Figure()

    # K线
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"], high=df["high"],
        low=df["low"],   close=df["close"],
        increasing_line_color="#E74C3C",
        decreasing_line_color="#27AE60",
        name="K线",
    ))

    # MA5 / MA20
    if len(df) >= 5:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["close"].rolling(5).mean(),
            mode="lines", line=dict(color="#F39C12", width=1.2),
            name="MA5",
        ))
    if len(df) >= 20:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["close"].rolling(20).mean(),
            mode="lines", line=dict(color="#9B59B6", width=1.2),
            name="MA20",
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=400,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=36, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        paper_bgcolor="white",
        plot_bgcolor="#F8F9FA",
    )
    fig.update_xaxes(gridcolor="#E0E0E0")
    fig.update_yaxes(gridcolor="#E0E0E0")

    st.plotly_chart(fig, use_container_width=True)


def render_metrics_row(df: pd.DataFrame, name_col: str, price_col: str, pct_col: str, n_cols: int = 3):
    """在多列中展示指标卡片"""
    if df is None or df.empty:
        st.info("数据加载中…")
        return
    cols = st.columns(min(n_cols, len(df)))
    for i, (_, row) in enumerate(df.iterrows()):
        col = cols[i % n_cols]
        with col:
            try:
                pct = float(row[pct_col])
                delta_str = f"{'+' if pct>=0 else ''}{pct:.2f}%"
                delta_color = "normal" if pct >= 0 else "inverse"
            except Exception:
                delta_str = str(row.get(pct_col, ""))
                delta_color = "off"
            st.metric(
                label=str(row[name_col]),
                value=str(row[price_col]),
                delta=delta_str,
            )


# ════════════════════════════════════════════════════════════════════
#  侧边栏
# ════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("📈 全球市场监控")
    st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    st.divider()

    page = st.radio(
        "导航",
        ["🏠 市场总览", "🤖 AI 早报", "🇺🇸 美股", "🇨🇳 A股", "📦 期货", "📊 K线图表"],
        label_visibility="collapsed",
    )

    st.divider()

    # Claude API 状态
    if not config.CLAUDE_API_KEY:
        st.warning("⚠️ AI未配置\n\n请在 config.py 填入 CLAUDE_API_KEY")
    else:
        st.success("✅ Claude AI 已连接")

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
    if st.button("🔄 立即刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"自动刷新间隔：{config.REFRESH_INTERVAL // 60} 分钟")


# ════════════════════════════════════════════════════════════════════
#  页面：市场总览
# ════════════════════════════════════════════════════════════════════
if page == "🏠 市场总览":
    st.title("🌍 全球金融市场总览")

    # ── 美股指数 ──
    st.markdown('<div class="section-title">🇺🇸 美股指数</div>', unsafe_allow_html=True)
    with st.spinner("加载美股指数…"):
        us_idx = load_us_index()
    render_metrics_row(us_idx, "名称", "现价", "涨跌幅%", n_cols=3)

    st.divider()

    # ── A股指数 ──
    st.markdown('<div class="section-title">🇨🇳 A股指数</div>', unsafe_allow_html=True)
    with st.spinner("加载A股指数…"):
        cn_idx = load_cn_index()
    render_metrics_row(cn_idx, "名称", "现价", "涨跌幅%", n_cols=3)

    st.divider()

    # ── 期货概览（能源+贵金属）──
    st.markdown('<div class="section-title">📦 大宗商品</div>', unsafe_allow_html=True)
    with st.spinner("加载期货数据…"):
        fut_df = load_futures()

    if not fut_df.empty:
        key_items = fut_df[fut_df["品种"].isin(["WTI原油", "黄金", "铜", "标普500期货", "纳指期货"])]
        render_metrics_row(key_items, "品种", "现价", "涨跌幅%", n_cols=5)

    st.divider()

    # ── 美股自选 ──
    st.markdown('<div class="section-title">⭐ 美股自选</div>', unsafe_allow_html=True)
    with st.spinner("加载自选股…"):
        us_df = load_us_data()
    if not us_df.empty:
        display_cols = ["名称", "现价", "涨跌额", "涨跌幅%", "更新时间"]
        available = [c for c in display_cols if c in us_df.columns]
        st.dataframe(
            style_table(us_df[available]),
            use_container_width=True,
            hide_index=True,
            height=300,
        )


# ════════════════════════════════════════════════════════════════════
#  页面：AI 早报
# ════════════════════════════════════════════════════════════════════
elif page == "🤖 AI 早报":
    st.title("🤖 AI 市场早报")

    if not config.CLAUDE_API_KEY:
        st.error("请先在 config.py 中填入 CLAUDE_API_KEY，然后重启应用。")
        with st.expander("如何填写？"):
            st.code("""# 打开 config.py，找到这一行：
CLAUDE_API_KEY = ""

# 改成（引号内填你的 Key）：
CLAUDE_API_KEY = "sk-ant-xxxxxx..."
""", language="python")
        st.stop()

    # 已缓存的早报
    if "brief_content" not in st.session_state:
        st.session_state.brief_content = ""
    if "brief_time" not in st.session_state:
        st.session_state.brief_time = ""

    col1, col2 = st.columns([3, 1])
    with col1:
        extra = st.text_input("特别关注（可选）", placeholder="例如：重点关注科技股、关注黄金走势")
    with col2:
        st.write("")
        st.write("")
        gen_btn = st.button("✨ 生成早报", use_container_width=True, type="primary")

    if gen_btn:
        with st.spinner("Claude 正在分析市场数据，请稍候…"):
            result = ai_brief.generate_morning_brief(extra_focus=extra)
            st.session_state.brief_content = result
            st.session_state.brief_time = datetime.now().strftime("%H:%M:%S")

    if st.session_state.brief_content:
        st.caption(f"生成时间：{st.session_state.brief_time}")
        st.markdown(st.session_state.brief_content)

        st.divider()
        st.download_button(
            label="📥 下载早报（txt）",
            data=st.session_state.brief_content,
            file_name=f"早报_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
        )
    else:
        st.info("点击「生成早报」按钮，Claude 将根据当前市场数据自动生成分析报告。")

        st.markdown("""
**早报包含：**
- 🇺🇸 隔夜美股三大指数表现与热门个股点评
- 🛢️ 大宗商品（黄金、原油、铜）动态分析
- 🇨🇳 今日 A 股开盘方向展望
- 📌 今日重点关注事件与风险提示
""")

    # ── 异常检测区域 ──
    st.divider()
    st.subheader("🔍 单标的快速分析")
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
elif page == "🇺🇸 美股":
    st.title("🇺🇸 美股行情")

    tab1, tab2 = st.tabs(["📋 自选股列表", "🔍 搜索查询"])

    with tab1:
        with st.spinner("加载数据…"):
            us_df = load_us_data()
        if not us_df.empty:
            # 涨跌榜
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🔴 涨幅榜 Top 5")
                top5 = us_df.nlargest(5, "涨跌幅%")[["名称", "现价", "涨跌幅%"]]
                st.dataframe(style_table(top5), hide_index=True, use_container_width=True)
            with col2:
                st.subheader("🟢 跌幅榜 Top 5")
                bot5 = us_df.nsmallest(5, "涨跌幅%")[["名称", "现价", "涨跌幅%"]]
                st.dataframe(style_table(bot5), hide_index=True, use_container_width=True)

            st.subheader("全部自选股")
            st.dataframe(style_table(us_df), use_container_width=True, hide_index=True)

    with tab2:
        symbol_input = st.text_input("输入美股代码（如 AAPL、TSLA）", "AAPL").upper()
        period_map = {"1个月": "1mo", "3个月": "3mo", "6个月": "6mo", "1年": "1y", "2年": "2y"}
        period_sel = st.selectbox("周期", list(period_map.keys()), index=2)

        if symbol_input:
            quote = us_stocks.get_quote([symbol_input])
            if not quote.empty:
                row = quote.iloc[0]
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("现价", row.get("现价", "—"))
                with c2: st.metric("涨跌幅", format_pct(row.get("涨跌幅%", 0)))
                with c3: st.metric("涨跌额", row.get("涨跌额", "—"))

            hist = load_us_history(symbol_input, period_map[period_sel])
            render_kline(hist, f"{symbol_input} K线图")


# ════════════════════════════════════════════════════════════════════
#  页面：A股
# ════════════════════════════════════════════════════════════════════
elif page == "🇨🇳 A股":
    st.title("🇨🇳 A股行情")

    if not tushare_ok:
        st.warning("请先在 config.py 中配置 Tushare Token，然后重启应用。")
        st.stop()

    # 北向资金
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

    st.divider()

    # 指数
    st.subheader("📊 主要指数")
    with st.spinner("加载指数…"):
        cn_idx = load_cn_index()
    if not cn_idx.empty:
        cols_show = [c for c in ["名称", "现价", "涨跌额", "涨跌幅%", "成交量(亿)"] if c in cn_idx.columns]
        st.dataframe(style_table(cn_idx[cols_show], pct_col="涨跌幅%"),
                     use_container_width=True, hide_index=True)

    st.divider()

    # 自选股
    st.subheader("⭐ 自选股")
    with st.spinner("加载自选股…"):
        cn_df = load_cn_stocks()
    if not cn_df.empty:
        cols_show = [c for c in ["名称", "代码", "现价", "涨跌额", "涨跌幅%", "成交量(亿)"] if c in cn_df.columns]
        st.dataframe(style_table(cn_df[cols_show], pct_col="涨跌幅%"),
                     use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════
#  页面：期货
# ════════════════════════════════════════════════════════════════════
elif page == "📦 期货":
    st.title("📦 期货行情")

    with st.spinner("加载期货数据…"):
        fut_df = load_futures()

    if fut_df.empty:
        st.error("期货数据加载失败，请检查网络连接")
    else:
        # 按分类展示
        for cat in fut_df["分类"].unique():
            st.markdown(f'<div class="section-title">{cat}</div>', unsafe_allow_html=True)
            sub = fut_df[fut_df["分类"] == cat].copy()
            cols_show = ["品种", "现价", "涨跌额", "涨跌幅%", "更新时间"]
            available = [c for c in cols_show if c in sub.columns]
            st.dataframe(
                style_table(sub[available]),
                use_container_width=True,
                hide_index=True,
            )
            st.write("")

        # 期货涨跌条形图
        st.subheader("涨跌幅对比")
        chart_df = fut_df[["品种", "涨跌幅%"]].copy()
        chart_df["颜色"] = chart_df["涨跌幅%"].apply(lambda x: "涨" if float(x) >= 0 else "跌")
        fig = px.bar(
            chart_df.sort_values("涨跌幅%"),
            x="涨跌幅%", y="品种", orientation="h",
            color="颜色",
            color_discrete_map={"涨": "#E74C3C", "跌": "#27AE60"},
            height=max(300, len(chart_df) * 28),
        )
        fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════
#  页面：K线图表
# ════════════════════════════════════════════════════════════════════
elif page == "📊 K线图表":
    st.title("📊 K线图表")

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
        period_map = {"1个月": "1mo", "3个月": "3mo", "6个月": "6mo", "1年": "1y"}
        period_sel = st.selectbox("周期", list(period_map.keys()), index=1)

    with st.spinner("加载K线数据…"):
        if market == "美股":
            hist = load_us_history(symbol, period_map[period_sel])
            title = symbol
        else:
            hist = load_futures_history(symbol, period_map[period_sel])
            title = name_sel if market == "期货（国际）" else symbol

    render_kline(hist, f"{title} — {period_sel}")

    if not hist.empty:
        with st.expander("查看原始数据"):
            st.dataframe(hist.tail(30), use_container_width=True)


# ─── 页脚 ──────────────────────────────────────────────────────────
st.markdown("---")
st.caption("数据来源：Yahoo Finance（美股/期货）· Tushare Pro（A股） | 延迟约15分钟，仅供参考，不构成投资建议")
