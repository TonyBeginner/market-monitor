"""
数据预热脚本 — 每天 0 点运行，提前拉取当日数据并缓存到磁盘。
用法：python warm_cache.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from utils import disk_cache
import config

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始预热缓存...")


def run(label: str, key: str, fn):
    print(f"  正在拉取: {label}...", end="", flush=True)
    try:
        data = fn()
        if data is not None and not (hasattr(data, "empty") and data.empty):
            disk_cache.save(key, data)
            print(" 完成")
        else:
            print(" 无数据，跳过")
    except Exception as e:
        print(f" 失败: {e}")


# ─── 美股 ─────────────────────────────────────────────────────────
from collectors import us_stocks
run("美股自选",  "us_data",  lambda: us_stocks.get_quote(config.MY_US_WATCHLIST))
run("美股指数",  "us_index", lambda: us_stocks.get_quote(["^GSPC", "^IXIC", "^DJI"]))
run("美股板块",  "sector_perf", us_stocks.get_sector_performance)
run("全球市场快照", "global_snapshot", lambda: us_stocks.get_quote([
    "^GSPC","^IXIC","^DJI","^FTSE","^GDAXI","^FCHI",
    "^N225","^HSI","000001.SS","^KS11","^STI","^AXJO"
]))

# ─── 国际期货 ──────────────────────────────────────────────────────
from collectors import futures
run("国际期货",  "intl_futures", lambda: futures.get_intl_futures_quote(config.MY_FUTURES_CATEGORIES))

# ─── 国内期货 ──────────────────────────────────────────────────────
run("国内期货",  "cn_futures", futures.get_cn_futures_quote)

# ─── A股（需要 Tushare Token）─────────────────────────────────────
if config.TUSHARE_TOKEN:
    from collectors import cn_stocks
    try:
        import tushare as ts
        cn_stocks._pro = ts.pro_api(token=config.TUSHARE_TOKEN)
        run("A股指数",  "cn_index",  cn_stocks.get_index_quote)
        run("A股自选",  "cn_stocks", lambda: cn_stocks.get_stock_quote(config.MY_CN_WATCHLIST))
        run("沪深港通历史", "hsgt_history", lambda: cn_stocks.get_hsgt_flow_history(days=30))
    except Exception as e:
        print(f"  Tushare 初始化失败: {e}")
else:
    print("  跳过 A股（未配置 TUSHARE_TOKEN）")

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 预热完成！")
