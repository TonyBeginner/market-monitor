"""
美股数据采集模块 - 使用 yfinance（免费，无需 API Key）
"""
import yfinance as yf
import pandas as pd
from datetime import datetime


# 默认监控列表
DEFAULT_US_STOCKS = {
    "指数": ["^GSPC", "^IXIC", "^DJI"],          # 标普500、纳斯达克、道琼斯
    "科技": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA"],
    "中概": ["BABA", "PDD", "JD", "BIDU"],
}

INDEX_NAMES = {
    "^GSPC": "标普500",
    "^IXIC": "纳斯达克",
    "^DJI":  "道琼斯",
}


def get_quote(symbols: list[str]) -> pd.DataFrame:
    """
    批量获取实时报价（延迟约15分钟）
    返回 DataFrame，列：symbol, name, price, change, change_pct, volume, market_cap
    """
    if not symbols:
        return pd.DataFrame()

    tickers = yf.Tickers(" ".join(symbols))
    rows = []

    for sym in symbols:
        try:
            info = tickers.tickers[sym].fast_info
            hist = tickers.tickers[sym].history(period="2d", interval="1d")

            if hist.empty or len(hist) < 1:
                continue

            raw_today = hist["Close"].iloc[-1]
            raw_prev  = hist["Close"].iloc[-2] if len(hist) >= 2 else raw_today

            # 跳过 NaN / None 值
            import pandas as pd
            if pd.isna(raw_today) or pd.isna(raw_prev):
                continue

            close_today = float(raw_today)
            close_prev  = float(raw_prev)
            change      = close_today - close_prev
            change_pct  = (change / close_prev * 100) if close_prev else 0

            mkt_cap = getattr(info, "market_cap", None)
            rows.append({
                "代码":     sym,
                "名称":     INDEX_NAMES.get(sym, sym),
                "现价":     round(close_today, 2),
                "涨跌额":   round(change, 2),
                "涨跌幅%":  round(change_pct, 2),
                "成交量":   getattr(info, "three_month_average_volume", 0) or 0,
                "市值(亿)": round(mkt_cap / 1e8, 1) if mkt_cap else 0,
                "更新时间": datetime.now().strftime("%H:%M:%S"),
            })
        except Exception as e:
            print(f"[US] {sym} 获取失败: {e}")

    return pd.DataFrame(rows)


def get_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    获取历史 K 线数据
    period: 1d 5d 1mo 3mo 6mo 1y 2y 5y
    interval: 1m 5m 15m 30m 60m 1d 1wk 1mo
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        return df.dropna()
    except Exception as e:
        print(f"[US] 历史数据获取失败 {symbol}: {e}")
        return pd.DataFrame()


def get_all_symbols() -> list[str]:
    """返回所有默认监控标的"""
    syms = []
    for group in DEFAULT_US_STOCKS.values():
        syms.extend(group)
    return syms
