"""
配置文件 - 在这里填入你的 API Token
"""

# ─── Claude API Key ──────────────────────────────────────────────
# 1. 前往 https://console.anthropic.com 注册
# 2. 进入 API Keys -> Create Key
# 3. 把 sk-ant-... 开头的 Key 填入下方
CLAUDE_API_KEY = "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"   # <-- 填你的 Claude API Key

# ─── Tushare Pro Token ───────────────────────────────────────────
# 1. 前往 https://tushare.pro 注册（免费）
# 2. 登录后在个人中心 -> 接口TOKEN 获取
# 3. 填入下方引号内
TUSHARE_TOKEN = ""   # <-- 填你的 Token，留空则 A 股数据不显示

# ─── 刷新间隔（秒）──────────────────────────────────────────────
REFRESH_INTERVAL = 300   # 默认5分钟刷新一次

# ─── 自选股列表（美股）──────────────────────────────────────────
# 直接填 Yahoo Finance 代码即可
MY_US_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA",
    "BABA", "PDD",
]

# ─── 自选股列表（A股）───────────────────────────────────────────
# 格式：Tushare ts_code，如 600519.SH
MY_CN_WATCHLIST = [
    "600519.SH",   # 贵州茅台
    "000858.SZ",   # 五粮液
    "601318.SH",   # 中国平安
    "600036.SH",   # 招商银行
    "002594.SZ",   # 比亚迪
]

# ─── 期货关注分类 ────────────────────────────────────────────────
# 可选: 能源 / 贵金属 / 工业金属 / 农产品 / 股指
MY_FUTURES_CATEGORIES = ["能源", "贵金属", "工业金属", "股指"]
