"""
期货数据采集模块 - 使用 yfinance 获取国际期货
国内期货通过 Tushare Pro 获取
"""
import yfinance as yf
import pandas as pd
from datetime import datetime


# 国际期货标的（yfinance 支持）
INTL_FUTURES = {
    "能源":   [("CL=F", "WTI原油"), ("BZ=F", "布伦特原油"), ("NG=F", "天然气")],
    "贵金属": [("GC=F", "黄金"),    ("SI=F", "白银"),        ("PL=F", "铂金")],
    "工业金属":[("HG=F", "铜"),     ("ALI=F", "铝")],
    "农产品": [("ZC=F", "玉米"),    ("ZW=F", "小麦"),        ("ZS=F", "大豆")],
    "股指":   [("ES=F", "标普500期货"), ("NQ=F", "纳指期货"), ("YM=F", "道指期货")],
}

# 国内期货（需要 Tushare，以下为合约代码示例）
CN_FUTURES = [
    ("IF.CFX", "沪深300股指期货"),
    ("IC.CFX", "中证500股指期货"),
    ("AU.SHF", "黄金期货(沪)"),
    ("CU.SHF", "铜期货"),
    ("RB.SHF", "螺纹钢"),
]


def get_intl_futures_quote(categories: list = None) -> pd.DataFrame:
    """
    获取国际期货实时报价
    categories: 指定分类，None 表示全部
    """
    rows = []
    target = INTL_FUTURES if not categories else {k: v for k, v in INTL_FUTURES.items() if k in categories}

    for cat, items in target.items():
        for symbol, name in items:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d", interval="1d")

                if hist.empty:
                    continue

                close_today = float(hist["Close"].iloc[-1])
                close_prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else close_today
                change      = close_today - close_prev
                change_pct  = (change / close_prev * 100) if close_prev else 0

                rows.append({
                    "分类":     cat,
                    "品种":     name,
                    "代码":     symbol,
                    "现价":     round(close_today, 2),
                    "涨跌额":   round(change, 2),
                    "涨跌幅%":  round(change_pct, 2),
                    "更新时间": datetime.now().strftime("%H:%M:%S"),
                })
            except Exception as e:
                print(f"[Futures] {symbol} 获取失败: {e}")

    return pd.DataFrame(rows)


def get_futures_history(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """
    获取期货历史价格数据
    symbol: 如 GC=F (黄金), CL=F (原油)
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        df.index = pd.to_datetime(df.index)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        return df.dropna()
    except Exception as e:
        print(f"[Futures] 历史数据获取失败 {symbol}: {e}")
        return pd.DataFrame()


def get_all_symbols() -> list[tuple]:
    """返回所有国际期货标的 (symbol, name) 列表"""
    result = []
    for items in INTL_FUTURES.values():
        result.extend(items)
    return result
