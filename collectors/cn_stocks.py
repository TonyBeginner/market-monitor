"""
A股数据采集模块 - 使用 Tushare Pro
需要在 config.py 填入你的 Tushare Token（免费注册即可获得）
"""
import pandas as pd
from datetime import datetime, date
import time

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False


# 默认监控列表
DEFAULT_CN_STOCKS = {
    "指数": [
        ("000001.SH", "上证综指"),
        ("000300.SH", "沪深300(IF)"),
        ("000905.SH", "中证500(IC)"),
        ("000852.SH", "中证1000(IM)"),
        ("000016.SH", "上证50(IH)"),
        ("399006.SZ", "创业板指"),
    ],
    "白马股": [
        ("600519.SH", "贵州茅台"),
        ("000858.SZ", "五粮液"),
        ("601318.SH", "中国平安"),
        ("600036.SH", "招商银行"),
        ("000333.SZ", "美的集团"),
    ],
    "科技": [
        ("002594.SZ", "比亚迪"),
        ("300750.SZ", "宁德时代"),
        ("688111.SH", "金山办公"),
    ],
}

_pro = None
_last_error = None


def init_tushare(token: str):
    """初始化 Tushare Pro 客户端"""
    global _pro, TUSHARE_AVAILABLE
    if not TUSHARE_AVAILABLE:
        return False
    try:
        _pro = ts.pro_api(token=token)
        # 简单测试连通性
        _pro.trade_cal(exchange="SSE", start_date="20240101", end_date="20240102")
        return True
    except Exception as e:
        print(f"[CN] Tushare 初始化失败: {e}")
        return False


def get_index_quote(token: str = None) -> pd.DataFrame:
    """
    获取主要指数实时行情（使用日线数据）
    """
    if not TUSHARE_AVAILABLE or _pro is None:
        return _get_mock_index_data()

    try:
        today = date.today().strftime("%Y%m%d")
        index_codes = [code for code, _ in DEFAULT_CN_STOCKS["指数"]]
        name_map    = {code: name for code, name in DEFAULT_CN_STOCKS["指数"]}

        # index_daily 不支持多代码拼接，逐个查询
        frames = []
        for code in index_codes:
            tmp = _pro.index_daily(ts_code=code, limit=1)
            if tmp is not None and not tmp.empty:
                frames.append(tmp.iloc[[0]])
        if not frames:
            return _get_mock_index_data()

        latest = pd.concat(frames, ignore_index=True)

        rows = []
        for _, row in latest.iterrows():
            rows.append({
                "代码":     row["ts_code"],
                "名称":     name_map.get(row["ts_code"], row["ts_code"]),
                "现价":     round(row["close"], 2),
                "涨跌额":   round(row["change"], 2),
                "涨跌幅%":  round(row["pct_chg"], 2),
                "成交量(亿)": round(row["vol"] / 1e4, 2) if row["vol"] else 0,
                "更新时间": datetime.now().strftime("%H:%M:%S"),
            })
        return pd.DataFrame(rows)

    except Exception as e:
        import traceback
        print(f"[CN] 指数行情获取失败: {e}")
        print(traceback.format_exc())
        # 将错误存入全局变量，方便 app.py 展示
        global _last_error
        _last_error = str(e)
        return _get_mock_index_data()


def get_stock_quote(ts_codes: list[str]) -> pd.DataFrame:
    """
    获取个股实时行情（日线）
    """
    if not TUSHARE_AVAILABLE or _pro is None:
        return pd.DataFrame()

    try:
        today = date.today().strftime("%Y%m%d")
        df = _pro.daily(
            ts_code=",".join(ts_codes),
            trade_date=today,
        )
        if df is None or df.empty:
            # 尝试最近交易日
            df = _pro.daily(ts_code=",".join(ts_codes))
            if df is not None and not df.empty:
                df = df[df["trade_date"] == df["trade_date"].max()]

        if df is None or df.empty:
            return pd.DataFrame()

        # 获取股票名称
        basic = _pro.stock_basic(
            ts_code=",".join(ts_codes),
            fields="ts_code,name"
        )
        name_map = dict(zip(basic["ts_code"], basic["name"])) if basic is not None else {}

        rows = []
        for _, row in df.iterrows():
            rows.append({
                "代码":     row["ts_code"],
                "名称":     name_map.get(row["ts_code"], row["ts_code"]),
                "现价":     round(row["close"], 2),
                "涨跌额":   round(row["change"], 2),
                "涨跌幅%":  round(row["pct_chg"], 2),
                "成交量(亿)": round(row["vol"] / 1e4, 2) if row["vol"] else 0,
                "更新时间": datetime.now().strftime("%H:%M:%S"),
            })
        return pd.DataFrame(rows)

    except Exception as e:
        print(f"[CN] 个股行情获取失败: {e}")
        return pd.DataFrame()


def get_history(ts_code: str, start: str = None, end: str = None) -> pd.DataFrame:
    """
    获取个股/指数历史日线数据
    ts_code: 如 000001.SH
    start/end: YYYYMMDD 格式
    """
    if not TUSHARE_AVAILABLE or _pro is None:
        return pd.DataFrame()

    try:
        if end is None:
            end = date.today().strftime("%Y%m%d")
        if start is None:
            # 默认近6个月
            from dateutil.relativedelta import relativedelta
            start = (date.today() - relativedelta(months=6)).strftime("%Y%m%d")

        # 区分指数和个股：优先按内置指数名单判断，避免 000905.SH 等被误判为股票
        index_codes = {code for code, _ in DEFAULT_CN_STOCKS["指数"]}
        if ts_code.endswith(".SH") or ts_code.endswith(".SZ"):
            if ts_code in index_codes or ts_code.startswith("399"):
                df = _pro.index_daily(ts_code=ts_code, start_date=start, end_date=end)
            else:
                df = _pro.daily(ts_code=ts_code, start_date=start, end_date=end)
        else:
            df = _pro.daily(ts_code=ts_code, start_date=start, end_date=end)

        if df is None or df.empty:
            return pd.DataFrame()

        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date").set_index("trade_date")
        df = df[["open", "high", "low", "close", "vol"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        return df.dropna()

    except Exception as e:
        print(f"[CN] 历史数据获取失败 {ts_code}: {e}")
        return pd.DataFrame()


def get_northbound_flow() -> dict:
    """获取北向资金最近交易日净流入（单位：亿元）"""
    if not TUSHARE_AVAILABLE or _pro is None:
        return {"north_money": None, "south_money": None, "trade_date": None, "error": "Tushare 未初始化"}
    try:
        # 查近 10 天，取最新一条，兼容周末/节假日
        end = date.today().strftime("%Y%m%d")
        from datetime import timedelta
        start = (date.today() - timedelta(days=10)).strftime("%Y%m%d")
        df = _pro.moneyflow_hsgt(start_date=start, end_date=end)
        if df is None or df.empty:
            return {"north_money": None, "south_money": None, "trade_date": None, "error": "API 返回空数据"}
        # 取最近一个交易日
        df = df.sort_values("trade_date", ascending=False)
        row = df.iloc[0]
        def _yi(key): return round(float(row.get(key) or 0) / 1e4, 2)
        return {
            "north_money": _yi("north_money"),
            "south_money": _yi("south_money"),
            "hgt":  _yi("hgt"),
            "sgt":  _yi("sgt"),
            "ggt_ss": _yi("ggt_ss"),
            "ggt_sz": _yi("ggt_sz"),
            "trade_date": str(row.get("trade_date", "")),
            "error": None,
        }
    except Exception as e:
        import traceback
        print(f"[CN] 北向资金获取失败: {e}")
        print(traceback.format_exc())
        return {"north_money": None, "south_money": None, "trade_date": None, "error": str(e)}


def get_hsgt_flow_history(days: int = 30) -> pd.DataFrame:
    """获取北向资金近 N 日成交额历史（返回 trade_date, north_money，单位亿）"""
    if not TUSHARE_AVAILABLE or _pro is None:
        return pd.DataFrame()
    try:
        end = date.today().strftime("%Y%m%d")
        from datetime import timedelta
        start = (date.today() - timedelta(days=days * 2)).strftime("%Y%m%d")
        df = _pro.moneyflow_hsgt(start_date=start, end_date=end)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.sort_values("trade_date").tail(days)
        for col in ["north_money", "hgt", "sgt"]:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 1e4
        return df[["trade_date", "north_money", "hgt", "sgt"]].reset_index(drop=True)
    except Exception as e:
        print(f"[CN] 北向成交历史获取失败: {e}")
        return pd.DataFrame()


def get_ggt_net_buy_latest() -> dict:
    """获取南向资金最新一日净买额（买入-卖出，单位：亿元）"""
    if not TUSHARE_AVAILABLE or _pro is None:
        return {"net_buy": None, "buy_amount": None, "sell_amount": None, "trade_date": None, "error": "Tushare 未初始化"}
    try:
        end = date.today().strftime("%Y%m%d")
        from datetime import timedelta
        start = (date.today() - timedelta(days=10)).strftime("%Y%m%d")
        df = _pro.ggt_daily(start_date=start, end_date=end)
        if df is None or df.empty:
            return {"net_buy": None, "buy_amount": None, "sell_amount": None, "trade_date": None, "error": "API 返回空数据"}
        df = df.sort_values("trade_date", ascending=False)
        row = df.iloc[0]
        buy = round(float(row.get("buy_amount") or 0), 2)
        sell = round(float(row.get("sell_amount") or 0), 2)
        net = round(buy - sell, 2)
        return {
            "net_buy": net,
            "buy_amount": buy,
            "sell_amount": sell,
            "trade_date": str(row.get("trade_date", "")),
            "error": None,
        }
    except Exception as e:
        print(f"[CN] 南向净买额获取失败: {e}")
        return {"net_buy": None, "buy_amount": None, "sell_amount": None, "trade_date": None, "error": str(e)}


def get_ggt_net_buy_history(days: int = 30) -> pd.DataFrame:
    """获取南向资金近 N 日净买额历史（buy_amount - sell_amount，单位亿元）"""
    if not TUSHARE_AVAILABLE or _pro is None:
        return pd.DataFrame()
    try:
        end = date.today().strftime("%Y%m%d")
        from datetime import timedelta
        start = (date.today() - timedelta(days=days * 2)).strftime("%Y%m%d")
        df = _pro.ggt_daily(start_date=start, end_date=end)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.sort_values("trade_date").tail(days)
        df["buy_amount"] = pd.to_numeric(df["buy_amount"], errors="coerce")
        df["sell_amount"] = pd.to_numeric(df["sell_amount"], errors="coerce")
        df["net_buy"] = df["buy_amount"] - df["sell_amount"]
        return df[["trade_date", "net_buy", "buy_amount", "sell_amount"]].reset_index(drop=True)
    except Exception as e:
        print(f"[CN] 南向净买历史获取失败: {e}")
        return pd.DataFrame()


def _get_mock_index_data() -> pd.DataFrame:
    """当 Tushare 未配置时返回示例数据（提示用户配置）"""
    return pd.DataFrame([
        {"代码": "000001.SH", "名称": "上证综指", "现价": "—", "涨跌额": "—", "涨跌幅%": "—", "成交量(亿)": "—", "更新时间": "未配置Token"},
        {"代码": "399001.SZ", "名称": "深证成指", "现价": "—", "涨跌额": "—", "涨跌幅%": "—", "成交量(亿)": "—", "更新时间": "未配置Token"},
        {"代码": "399006.SZ", "名称": "创业板指", "现价": "—", "涨跌额": "—", "涨跌幅%": "—", "成交量(亿)": "—", "更新时间": "未配置Token"},
    ])
