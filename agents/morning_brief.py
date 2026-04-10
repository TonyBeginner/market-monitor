"""
每日市场早报 Agent
使用 Claude API 根据实时市场数据生成中文早报
"""
import anthropic
import json
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from collectors import us_stocks, futures


def _gather_market_data() -> dict:
    """采集当前市场数据，整理成结构化字典"""

    # 美股指数
    us_idx = us_stocks.get_quote(["^GSPC", "^IXIC", "^DJI"])
    us_idx_list = []
    for _, row in us_idx.iterrows():
        us_idx_list.append({
            "名称": row.get("名称", ""),
            "现价": row.get("现价", ""),
            "涨跌幅": f"{row.get('涨跌幅%', 0):+.2f}%",
        })

    # 美股自选
    us_stocks_data = us_stocks.get_quote(config.MY_US_WATCHLIST)
    us_stocks_list = []
    for _, row in us_stocks_data.iterrows():
        us_stocks_list.append({
            "代码": row.get("名称", ""),
            "现价": row.get("现价", ""),
            "涨跌幅": f"{row.get('涨跌幅%', 0):+.2f}%",
        })

    # 大宗商品
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
    """
    调用 Claude API 生成每日早报
    extra_focus: 用户指定的额外关注点，如"重点关注科技股"
    返回格式化的早报字符串
    """
    if not config.CLAUDE_API_KEY:
        return "❌ 请先在 config.py 中填入 CLAUDE_API_KEY"

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
简述三大指数表现，点评1-2只涨跌幅最大的个股原因（根据你的知识推断市场逻辑）

**【大宗商品】**
简述黄金、原油、铜等关键品种表现及背后逻辑

**【今日A股展望】**
根据隔夜外盘情绪，预判A股早盘方向，点出需关注的板块

**【今日重点关注】**
列出2-3个今日值得关注的事件或风险点（结合你的知识）

{"**用户特别关注：**" + extra_focus if extra_focus else ""}

语气专业但易懂，避免废话，直接给出判断。"""

    try:
        client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        brief = message.content[0].text
        header = (
            f"📰 **全球市场早报** · {data['日期']} {data['时间']}\n\n"
            f"{'━' * 40}\n\n"
        )
        return header + brief
    except anthropic.AuthenticationError:
        return "❌ Claude API Key 无效，请检查 config.py 中的 CLAUDE_API_KEY 是否正确"
    except Exception as e:
        return f"❌ AI 分析失败：{e}"


def analyze_anomaly(symbol: str, name: str, change_pct: float, market: str = "美股") -> str:
    """
    异常涨跌分析：当某标的涨跌幅超过阈值时，调用 Claude 解释原因
    symbol: 代码
    name: 名称
    change_pct: 涨跌幅（如 -5.2）
    market: 美股 / A股 / 期货
    """
    if not config.CLAUDE_API_KEY:
        return "请配置 CLAUDE_API_KEY"

    direction = "上涨" if change_pct > 0 else "下跌"
    prompt = (
        f"今日{market}市场，{name}（{symbol}）{direction}{abs(change_pct):.2f}%，"
        f"属于{'较大涨幅' if change_pct > 0 else '较大跌幅'}。"
        f"请用2-3句话简洁分析可能的原因（基于你的知识推断市场逻辑）。"
        f"直接给出分析，不要有开场白。"
    )

    try:
        client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",   # 用快速模型，降低成本
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        return f"分析失败：{e}"


if __name__ == "__main__":
    # 直接运行此文件可测试早报生成
    print("正在生成早报...")
    brief = generate_morning_brief()
    print(brief)
