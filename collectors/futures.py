"""
期货数据采集模块
- 国际期货：yfinance
- 国内期货：AKShare（东方财富实时行情）
"""
import yfinance as yf
import pandas as pd
from datetime import datetime

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


def _to_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _get_fast_info_value(info, key: str, default=None):
    if isinstance(info, dict):
        return info.get(key, default)
    return getattr(info, key, default)


# 国际期货标的（yfinance 支持）
INTL_FUTURES = {
    "能源":    [("CL=F", "WTI原油"), ("BZ=F", "布伦特原油"), ("NG=F", "天然气")],
    "贵金属":  [("GC=F", "黄金"),    ("SI=F", "白银"),        ("PL=F", "铂金")],
    "工业金属":[("HG=F", "铜"),      ("ALI=F", "铝")],
    "农产品":  [("ZC=F", "玉米"),    ("ZW=F", "小麦"),        ("ZS=F", "大豆")],
    "股指":    [("ES=F", "标普500期货"), ("NQ=F", "纳指期货"), ("YM=F", "道指期货")],
}

# 国内期货关注品种（按分类）：(显示名, akshare新浪symbol)
CN_FUTURES_WATCH = {
    "股指期货": [("沪深300", "沪深300指数期货"), ("中证500", "中证500指数期货"), ("上证50", "上证50指数期货"), ("中证1000", "中证1000股指期货")],
    "黑色系":   [("螺纹钢", "螺纹钢"), ("铁矿石", "铁矿石"), ("热轧卷板", "热轧卷板"), ("焦炭", "焦炭"), ("焦煤", "焦煤")],
    "有色金属": [("沪铜", "沪铜"), ("沪铝", "沪铝"), ("沪锌", "沪锌"), ("沪镍", "沪镍"), ("沪锡", "沪锡")],
    "贵金属":   [("沪金", "黄金"), ("沪银", "白银")],
    "能源化工": [("原油", "原油"), ("PTA", "PTA"), ("甲醇", "郑醇"), ("液化石油气", "液化石油气")],
    "农产品":   [("豆粕", "豆粕"), ("豆油", "豆油"), ("棕榈油", "棕榈"), ("玉米", "玉米"), ("玉米淀粉", "玉米淀粉")],
}


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
                close_today = None
                close_prev = None

                try:
                    info = ticker.fast_info or {}
                except Exception:
                    info = {}

                close_today = _to_float(
                    _get_fast_info_value(info, "lastPrice")
                    or _get_fast_info_value(info, "regularMarketPrice")
                    or _get_fast_info_value(info, "last_price")
                )
                close_prev = _to_float(
                    _get_fast_info_value(info, "previousClose")
                    or _get_fast_info_value(info, "previous_close")
                )

                if close_today is None or close_prev in (None, 0):
                    hist = ticker.history(period="5d", interval="1d")
                    if hist is None or hist.empty or "Close" not in hist:
                        continue
                    closes = pd.to_numeric(hist["Close"], errors="coerce").dropna()
                    if closes.empty:
                        continue
                    if close_today is None:
                        close_today = float(closes.iloc[-1])
                    if close_prev in (None, 0):
                        close_prev = float(closes.iloc[-2]) if len(closes) >= 2 else close_today

                if close_today is None:
                    continue
                if close_prev in (None, 0):
                    close_prev = close_today

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


def get_futures_history(symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """
    获取期货历史价格数据
    symbol: 如 GC=F (黄金), CL=F (原油)
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        return df.dropna()
    except Exception as e:
        print(f"[Futures] 历史数据获取失败 {symbol}: {e}")
        return pd.DataFrame()


def get_cn_futures_quote() -> pd.DataFrame:
    """
    获取国内期货实时行情（AKShare 新浪）
    返回 DataFrame，列：分类, 品种, 现价, 涨跌额, 涨跌幅%, 成交量(万手), 更新时间
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()

    rows = []
    for cat, items in CN_FUTURES_WATCH.items():
        for display_name, ak_symbol in items:
            try:
                df = ak.futures_zh_realtime(symbol=ak_symbol)
                if df.empty:
                    continue
                # 优先取连续合约行，否则取第一行
                cont = df[df["name"].str.contains("连续", na=False)]
                row = cont.iloc[0] if not cont.empty else df.iloc[0]

                trade = float(row.get("trade", 0) or 0)
                presettlement = float(row.get("presettlement", 0) or 0)
                if presettlement and trade:
                    change = round(trade - presettlement, 2)
                    change_pct = round(change / presettlement * 100, 2)
                else:
                    change, change_pct = 0.0, 0.0
                volume = float(row.get("volume", 0) or 0)

                rows.append({
                    "分类":        cat,
                    "品种":        display_name,
                    "现价":        round(trade, 2),
                    "涨跌额":      change,
                    "涨跌幅%":     change_pct,
                    "成交量(万手)": round(volume / 1e4, 1) if volume > 1e4 else round(volume, 0),
                    "更新时间":    datetime.now().strftime("%H:%M:%S"),
                })
            except Exception as e:
                print(f"[CN Futures] {display_name} 获取失败: {e}")

    if not rows:
        return pd.DataFrame()

    df_out = pd.DataFrame(rows)
    cat_order = list(CN_FUTURES_WATCH.keys())
    df_out["_order"] = df_out["分类"].map({c: i for i, c in enumerate(cat_order)})
    df_out = df_out.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    return df_out


def get_all_symbols() -> list[tuple]:
    """返回所有国际期货标的 (symbol, name) 列表"""
    result = []
    for items in INTL_FUTURES.values():
        result.extend(items)
    return result
