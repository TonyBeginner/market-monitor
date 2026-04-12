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


STOCK_DISPLAY_NAMES = {
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
}


def _get_display_name(ticker, sym: str) -> str:
    if sym in INDEX_NAMES:
        return INDEX_NAMES[sym]
    if sym in STOCK_DISPLAY_NAMES:
        return STOCK_DISPLAY_NAMES[sym]
    try:
        info = ticker.info or {}
        return (
            info.get("shortName")
            or info.get("longName")
            or info.get("displayName")
            or sym
        )
    except Exception:
        return sym


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
            display_name = _get_display_name(ticker, sym)

            rows.append(
                {
                    "代码": sym,
                    "名称": display_name,
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


# 美股板块 ETF（SPDR 系列）
SECTOR_ETFS = {
    "XLK":  "科技",
    "XLC":  "通信服务",
    "XLY":  "消费者可选",
    "XLP":  "消费者必选",
    "XLF":  "金融",
    "XLV":  "医疗保健",
    "XLI":  "工业",
    "XLB":  "原材料",
    "XLRE": "房地产",
    "XLE":  "能源",
    "XLU":  "公用事业",
}

# S&P 500 各板块权重（%），用于 Treemap 面积大小，无需实时抓取
SECTOR_SP500_WEIGHT = {
    "XLK":  32.0,
    "XLF":  13.2,
    "XLV":  12.4,
    "XLC":   8.9,
    "XLY":  10.1,
    "XLI":   8.3,
    "XLP":   5.9,
    "XLE":   3.6,
    "XLB":   2.3,
    "XLU":   2.4,
    "XLRE":  2.2,
}

# 各板块代表性成分股与相对权重（近似展示用）
SECTOR_COMPONENTS = {
    "科技": [("NVDA", 24), ("AAPL", 22), ("MSFT", 26), ("AVGO", 12), ("ORCL", 8), ("CRM", 8)],
    "通信服务": [("GOOGL", 36), ("META", 34), ("NFLX", 12), ("DIS", 10), ("TMUS", 8)],
    "消费者可选": [("AMZN", 34), ("TSLA", 24), ("HD", 12), ("MCD", 10), ("BKNG", 10), ("NKE", 10)],
    "消费者必选": [("WMT", 24), ("COST", 20), ("PG", 18), ("KO", 14), ("PEP", 14), ("PM", 10)],
    "金融": [("BRKB", 26), ("JPM", 22), ("V", 16), ("MA", 14), ("BAC", 12), ("GS", 10)],
    "医疗保健": [("LLY", 24), ("UNH", 18), ("JNJ", 16), ("MRK", 14), ("ABBV", 14), ("PFE", 14)],
    "工业": [("GE", 18), ("RTX", 18), ("CAT", 18), ("UBER", 14), ("HON", 16), ("UNP", 16)],
    "原材料": [("LIN", 28), ("SHW", 18), ("APD", 16), ("ECL", 14), ("FCX", 14), ("NEM", 10)],
    "房地产": [("AMT", 22), ("PLD", 22), ("EQIX", 18), ("WELL", 14), ("O", 12), ("SPG", 12)],
    "能源": [("XOM", 34), ("CVX", 28), ("COP", 14), ("SLB", 10), ("EOG", 8), ("MPC", 6)],
    "公用事业": [("NEE", 22), ("SO", 18), ("DUK", 18), ("CEG", 16), ("AEP", 14), ("SRE", 12)],
}


def get_sector_performance() -> pd.DataFrame:
    """获取美股各板块 ETF 当日涨跌幅及 AUM（作为市值权重）"""
    rows = []
    for symbol, name in SECTOR_ETFS.items():
        try:
            hist = yf.Ticker(symbol).history(period="2d", interval="1d")
            if len(hist) < 2:
                continue
            prev = float(hist["Close"].iloc[-2])
            curr = float(hist["Close"].iloc[-1])
            pct  = (curr - prev) / prev * 100
            weight = SECTOR_SP500_WEIGHT.get(symbol, 2.0)
            rows.append({"板块": name, "代码": symbol, "涨跌幅%": round(pct, 2), "AUM": weight})
        except Exception as e:
            print(f"[Sector] {symbol} 失败: {e}")
    return pd.DataFrame(rows)


def get_sector_constituent_performance() -> pd.DataFrame:
    """获取美股板块代表成分股表现，用于层级热力图。"""
    rows = []
    symbols = []
    for items in SECTOR_COMPONENTS.values():
        symbols.extend(sym for sym, _ in items)
    quote_df = get_quote(list(dict.fromkeys(symbols)))
    if quote_df.empty:
        return pd.DataFrame()

    quote_map = quote_df.set_index("代码").to_dict("index")
    for sector, items in SECTOR_COMPONENTS.items():
        for sym, weight in items:
            row = quote_map.get(sym)
            if not row:
                continue
            rows.append({
                "板块": sector,
                "代码": sym,
                "名称": row.get("名称", sym),
                "涨跌幅%": row.get("涨跌幅%", 0),
                "权重": weight,
            })
    return pd.DataFrame(rows)


def get_earnings_calendar(symbols: list[str]) -> pd.DataFrame:
    """获取自选股未来 30 天内的财报日期"""
    from datetime import date, timedelta
    today = date.today()
    cutoff = today + timedelta(days=30)
    rows = []
    for sym in symbols:
        try:
            cal = yf.Ticker(sym).calendar
            if cal is None:
                continue
            # yfinance 返回格式随版本变化
            if isinstance(cal, dict):
                dates = cal.get("Earnings Date") or []
                earn_date = dates[0] if dates else None
            else:
                earn_date = None
            if earn_date is None:
                continue
            d = pd.Timestamp(earn_date).date()
            if today <= d <= cutoff:
                rows.append({"代码": sym, "日期": d})
        except Exception as e:
            print(f"[Earnings] {sym} 失败: {e}")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("日期").reset_index(drop=True)
    return df
