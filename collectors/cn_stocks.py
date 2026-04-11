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
        ("399001.SZ", "深证成指"),
        ("399006.SZ", "创业板指"),
        ("000300.SH", "沪深300"),
        ("000905.SH", "中证500"),
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
        ("600测.SH", "宁德时代"),  # 占位示例
        ("688111.SH", "金山办公"),
    ],
}

_pro = None


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
        print(f"[CN] 指数行情获取失败: {e}")
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

        # 区分指数和个股
        if ts_code.endswith(".SH") or ts_code.endswith(".SZ"):
            if ts_code.startswith("0000") or ts_code.startswith("3990"):
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
    """获取北向资金今日净流入（单位：亿元）"""
    if not TUSHARE_AVAILABLE or _pro is None:
        return {"north_money": None, "south_money": None}
    try:
        today = date.today().strftime("%Y%m%d")
        df = _pro.moneyflow_hsgt(trade_date=today)
        if df is None or df.empty:
            return {"north_money": None, "south_money": None}
        row = df.iloc[0]
        return {
            "north_money": round(row.get("north_money", 0) / 1e4, 2),  # 转亿元
            "south_money": round(row.get("south_money", 0) / 1e4, 2),
        }
    except Exception:
        return {"north_money": None, "south_money": None}


def _get_mock_index_data() -> pd.DataFrame:
    """当 Tushare 未配置时返回示例数据（提示用户配置）"""
    return pd.DataFrame([
        {"代码": "000001.SH", "名称": "上证综指", "现价": "—", "涨跌额": "—", "涨跌幅%": "—", "成交量(亿)": "—", "更新时间": "未配置Token"},
        {"代码": "399001.SZ", "名称": "深证成指", "现价": "—", "涨跌额": "—", "涨跌幅%": "—", "成交量(亿)": "—", "更新时间": "未配置Token"},
        {"代码": "399006.SZ", "名称": "创业板指", "现价": "—", "涨跌额": "—", "涨跌幅%": "—", "成交量(亿)": "—", "更新时间": "未配置Token"},
    ])
