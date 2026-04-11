"""
美股数据采集模块 - 使用 yfinance（免费，无需 API Key）
"""
from datetime import datetime

import pandas as pd
import yfinance as yf


DEFAULT_US_STOCKS = {
    "指数": ["^GSPC", "^IXIC", "^DJI"],
    "科技": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA"],
    "中概": ["BABA", "PDD", "JD", "BIDU"],
}

INDEX_NAMES = {
    "^GSPC": "标普500",
    "^IXIC": "纳斯达克",
    "^DJI": "道琼斯",
}


def _get_fast_info_value(info, key: str, default=None):
    if isinstance(info, dict):
        return info.get(key, default)
    return getattr(info, key, default)


def get_quote(symbols: list[str]) -> pd.DataFrame:
    """
    批量获取实时报价（通常为延迟行情）
    返回列：代码、名称、现价、涨跌额、涨跌幅、成交量、市值(亿)、更新时间
    """
    if not symbols:
        return pd.DataFrame()

    tickers = yf.Tickers(" ".join(symbols))
    rows = []

    for sym in symbols:
        try:
            ticker = tickers.tickers.get(sym) or yf.Ticker(sym)
            hist = ticker.history(period="2d", interval="1d")

            if hist.empty:
                continue

            raw_today = hist["Close"].iloc[-1]
            raw_prev = hist["Close"].iloc[-2] if len(hist) >= 2 else raw_today

            if pd.isna(raw_today) or pd.isna(raw_prev):
                continue

            close_today = float(raw_today)
            close_prev = float(raw_prev)
            change = close_today - close_prev
            change_pct = (change / close_prev * 100) if close_prev else 0

            try:
                info = ticker.fast_info or {}
            except Exception:
                info = {}

            market_cap = _get_fast_info_value(info, "market_cap")
            avg_volume = _get_fast_info_value(info, "three_month_average_volume", 0) or 0

            rows.append(
                {
                    "代码": sym,
                    "名称": INDEX_NAMES.get(sym, sym),
                    "现价": round(close_today, 2),
                    "涨跌额": round(change, 2),
                    "涨跌幅%": round(change_pct, 2),
                    "涨跌幅": round(change_pct, 2),
                    "成交量": avg_volume,
                    "市值(亿)": round(market_cap / 1e8, 1) if market_cap else 0,
                    "更新时间": datetime.now().strftime("%H:%M:%S"),
                }
            )
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
