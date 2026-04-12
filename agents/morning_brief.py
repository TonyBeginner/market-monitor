"""
每日市场早报 Agent
优先使用 Groq（免费），没有 Groq Key 时降级到 Claude。
"""
import json
from datetime import datetime
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from collectors import us_stocks, futures
from utils.ai_client import chat


def _gather_market_data() -> dict:
    """采集当前市场数据，整理成结构化字典"""

    us_idx = us_stocks.get_quote(["^GSPC", "^IXIC", "^DJI"])
    us_idx_list = []
    for _, row in us_idx.iterrows():
        us_idx_list.append({
            "名称": row.get("名称", ""),
            "现价": row.get("现价", ""),
            "涨跌幅": f"{row.get('涨跌幅%', 0):+.2f}%",
        })

    us_stocks_data = us_stocks.get_quote(config.MY_US_WATCHLIST)
    us_stocks_list = []
    for _, row in us_stocks_data.iterrows():
        us_stocks_list.append({
            "代码": row.get("名称", ""),
            "现价": row.get("现价", ""),
            "涨跌幅": f"{row.get('涨跌幅%', 0):+.2f}%",
        })

    fut_df = futures.get_intl_futures_quote(["能源", "贵金属", "工业金属"])
    fut_list = []
    for _, row in fut_df.iterrows():
        fut_list.append({
            "品种": row.get("品种", ""),
            "现价": row.get("现价", ""),
            "涨跌幅": f"{row.get('涨跌幅%', 0):+.2f}%",
        })

    return {
        "日期": datetime.now().strftime("%Y年%m月%d日"),
        "时间": datetime.now().strftime("%H:%M"),
        "美股指数": us_idx_list,
        "美股个股": us_stocks_list,
        "大宗商品": fut_list,
    }


def generate_morning_brief(extra_focus: str = "") -> str:
    groq_key   = getattr(config, "GROQ_API_KEY",   "") or ""
    claude_key = getattr(config, "CLAUDE_API_KEY", "") or ""

    if not groq_key and not claude_key:
        return "❌ 请配置 GROQ_API_KEY（免费）或 CLAUDE_API_KEY"

    try:
        data = _gather_market_data()
    except Exception as e:
        return f"❌ 市场数据采集失败：{e}"

    data_json = json.dumps(data, ensure_ascii=False, indent=2)

    prompt = f"""你是一位专业的金融市场分析师，请根据以下实时市场数据，用中文生成一份简洁的每日市场早报。

## 当前市场数据
{data_json}

## 早报要求
请按以下结构输出，每个部分简洁有力，总字数控制在400字以内：

**【隔夜美股】**
简述三大指数表现，点评1-2只涨跌幅最大的个股原因

**【大宗商品】**
简述黄金、原油、铜等关键品种表现及背后逻辑

**【今日A股展望】**
根据隔夜外盘情绪，预判A股早盘方向，点出需关注的板块

**【今日重点关注】**
列出2-3个今日值得关注的事件或风险点

{"**用户特别关注：**" + extra_focus if extra_focus else ""}

语气专业但易懂，避免废话，直接给出判断。"""

    try:
        result = chat(prompt, api_key_groq=groq_key, api_key_claude=claude_key, max_tokens=1024)
        if not result:
            return "❌ AI 返回为空，请检查 API Key 是否有效"
        header = (
            f"📰 **全球市场早报** · {data['日期']} {data['时间']}\n\n"
            f"{'━' * 40}\n\n"
        )
        return header + result
    except Exception as e:
        return f"❌ AI 分析失败：{e}"


def analyze_anomaly(symbol: str, name: str, change_pct: float, market: str = "美股") -> str:
    groq_key   = getattr(config, "GROQ_API_KEY",   "") or ""
    claude_key = getattr(config, "CLAUDE_API_KEY", "") or ""

    if not groq_key and not claude_key:
        return "请配置 GROQ_API_KEY 或 CLAUDE_API_KEY"

    direction = "上涨" if change_pct > 0 else "下跌"
    prompt = (
        f"今日{market}市场，{name}（{symbol}）{direction}{abs(change_pct):.2f}%，"
        f"属于{'较大涨幅' if change_pct > 0 else '较大跌幅'}。"
        f"请用2-3句话简洁分析可能的原因（基于你的知识推断市场逻辑）。"
        f"直接给出分析，不要有开场白。"
    )

    try:
        return chat(prompt, api_key_groq=groq_key, api_key_claude=claude_key, max_tokens=200)
    except Exception as e:
        return f"分析失败：{e}"


def analyze_earnings(symbol: str, name: str) -> str:
    """
    抓取个股最近季度财报数据，用 AI 生成解读 + 未来预期。
    返回 Markdown 格式字符串。
    """
    groq_key   = getattr(config, "GROQ_API_KEY",   "") or ""
    claude_key = getattr(config, "CLAUDE_API_KEY", "") or ""
    if not groq_key and not claude_key:
        return "❌ 请配置 GROQ_API_KEY 或 CLAUDE_API_KEY"

    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)

        # 最近 4 个季度的财务数据
        qf = ticker.quarterly_financials
        qi = ticker.quarterly_income_stmt

        rows = []
        src = qi if (qi is not None and not qi.empty) else qf
        if src is not None and not src.empty:
            for col in list(src.columns)[:4]:
                period = str(col)[:10]
                revenue = src.loc["Total Revenue", col] if "Total Revenue" in src.index else None
                net_income = src.loc["Net Income", col] if "Net Income" in src.index else None
                rows.append({
                    "季度": period,
                    "营收(亿USD)": f"{revenue/1e8:.1f}" if revenue else "N/A",
                    "净利润(亿USD)": f"{net_income/1e8:.1f}" if net_income else "N/A",
                })

        # 分析师预期 EPS
        try:
            info = ticker.info
            forward_pe  = info.get("forwardPE", "N/A")
            peg_ratio   = info.get("pegRatio", "N/A")
            target_price = info.get("targetMeanPrice", "N/A")
            analyst_rec  = info.get("recommendationKey", "N/A")
        except Exception:
            forward_pe = peg_ratio = target_price = analyst_rec = "N/A"

        data_str = json.dumps({
            "股票": f"{name}（{symbol}）",
            "最近季报": rows,
            "预期市盈率": forward_pe,
            "PEG": peg_ratio,
            "分析师目标价": target_price,
            "分析师评级": analyst_rec,
        }, ensure_ascii=False, indent=2)

        prompt = f"""请根据以下{name}（{symbol}）的最新财报数据，用中文给出：

{data_str}

**请按以下结构输出（总字数250字以内）：**

**【上季财报解读】**
简述最近一季收入/利润表现，是否超预期，亮点或隐忧

**【分析师预期】**
目标价、评级及市场共识

**【未来展望】**
基于业务趋势和宏观环境，简述1-2个关键风险或催化剂

语气专业简洁，直接给判断，无需开场白。"""

        result = chat(prompt, api_key_groq=groq_key, api_key_claude=claude_key, max_tokens=600)
        return result if result else "❌ AI 返回为空"
    except Exception as e:
        return f"❌ 财报分析失败：{e}"


def _build_price_snapshot(hist: "pd.DataFrame") -> str:
    """将 K 线压缩成适合 AI 读取的走势摘要。"""
    if hist is None or hist.empty:
        return "{}"

    df = hist.tail(90).copy()
    latest = df.iloc[-1]
    first_close = float(df["close"].iloc[0])
    last_close = float(latest["close"])
    high = float(df["high"].max())
    low = float(df["low"].min())
    ret_all = ((last_close / first_close) - 1) * 100 if first_close else 0

    def _chg(window: int):
        if len(df) <= window:
            return None
        prev = float(df["close"].iloc[-window - 1])
        return round((last_close / prev - 1) * 100, 2) if prev else None

    ma5 = float(df["close"].tail(5).mean())
    ma20 = float(df["close"].tail(20).mean()) if len(df) >= 20 else None
    ma60 = float(df["close"].tail(60).mean()) if len(df) >= 60 else None
    avg_vol20 = float(df["volume"].tail(20).mean()) if "volume" in df.columns and len(df) >= 20 else None
    vol_ratio = None
    if avg_vol20 and latest.get("volume") is not None:
        try:
            vol_ratio = round(float(latest["volume"]) / avg_vol20, 2) if avg_vol20 else None
        except Exception:
            vol_ratio = None

    summary = {
        "样本K线数": int(len(df)),
        "区间起点收盘": round(first_close, 4),
        "最新收盘": round(last_close, 4),
        "区间涨跌幅%": round(ret_all, 2),
        "区间最高": round(high, 4),
        "区间最低": round(low, 4),
        "近5日涨跌幅%": _chg(5),
        "近20日涨跌幅%": _chg(20),
        "MA5": round(ma5, 4),
        "MA20": round(ma20, 4) if ma20 is not None else None,
        "MA60": round(ma60, 4) if ma60 is not None else None,
        "最新成交量/20日均量": vol_ratio,
        "最近10根K线收盘": [round(float(x), 4) for x in df["close"].tail(10).tolist()],
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)


def analyze_market_asset(symbol: str, name: str, asset_type: str, hist: "pd.DataFrame") -> str:
    """指数/期货：输出走势复盘 + AI前景分析。"""
    groq_key = getattr(config, "GROQ_API_KEY", "") or ""
    claude_key = getattr(config, "CLAUDE_API_KEY", "") or ""
    if not groq_key and not claude_key:
        return "❌ 请先配置 GROQ_API_KEY 或 CLAUDE_API_KEY"
    if hist is None or hist.empty:
        return "暂无足够的历史走势数据"

    snapshot = _build_price_snapshot(hist)
    prompt = f"""请根据以下{name}（{symbol}）的K线走势摘要，用中文输出两段简洁分析。

资产类别：{asset_type}
走势摘要：
{snapshot}

输出要求：
1. 先写 **【AI复盘走势】**：总结近一段时间趋势、节奏、关键转折、强弱特征。
2. 再写 **【AI前景分析】**：判断短中期更可能的演绎方向，并点出2-3个风险或催化。
3. 语言务实直接，不要写免责声明，不要假装看到了新闻。
4. 总长度控制在300字以内。
"""
    try:
        result = chat(prompt, api_key_groq=groq_key, api_key_claude=claude_key, max_tokens=500)
        return result if result else "❌ AI 返回为空"
    except Exception as e:
        return f"❌ AI 分析失败：{e}"


def analyze_stock_detail(symbol: str, name: str, hist: "pd.DataFrame") -> str:
    """股票：输出上一份财报解读 + AI前景分析。"""
    groq_key = getattr(config, "GROQ_API_KEY", "") or ""
    claude_key = getattr(config, "CLAUDE_API_KEY", "") or ""
    if not groq_key and not claude_key:
        return "❌ 请先配置 GROQ_API_KEY 或 CLAUDE_API_KEY"

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        src = ticker.quarterly_income_stmt
        if src is None or src.empty:
            src = ticker.quarterly_financials

        latest_quarter = {}
        if src is not None and not src.empty:
            col = list(src.columns)[0]
            latest_quarter = {
                "季度": str(col)[:10],
                "营收": src.loc["Total Revenue", col] if "Total Revenue" in src.index else None,
                "净利润": src.loc["Net Income", col] if "Net Income" in src.index else None,
                "营业利润": src.loc["Operating Income", col] if "Operating Income" in src.index else None,
            }

        try:
            info = ticker.info
        except Exception:
            info = {}

        payload = {
            "股票": f"{name} ({symbol})",
            "最新财报": latest_quarter,
            "forwardPE": info.get("forwardPE"),
            "targetMeanPrice": info.get("targetMeanPrice"),
            "recommendationKey": info.get("recommendationKey"),
            "走势摘要": json.loads(_build_price_snapshot(hist)),
        }
        prompt = f"""请基于以下{name}（{symbol}）的数据，用中文输出两段简洁分析：

{json.dumps(payload, ensure_ascii=False, indent=2)}

输出要求：
1. 先写 **【AI上一份财报】**：解读最近一季财报质量、亮点和隐忧。
2. 再写 **【AI前景分析】**：结合估值、业务趋势和股价结构，判断后续看点与风险。
3. 不要写免责声明，不要空话，总长度控制在320字以内。
"""
        result = chat(prompt, api_key_groq=groq_key, api_key_claude=claude_key, max_tokens=550)
        return result if result else "❌ AI 返回为空"
    except Exception as e:
        return f"❌ 股票分析失败：{e}"


if __name__ == "__main__":
    print("正在生成早报...")
    print(generate_morning_brief())
