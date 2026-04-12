"""
磁盘缓存工具
- 按日期存储，每天 0 点后自动使用新文件
- 格式：cache/YYYY-MM-DD_<key>.pkl
"""
import pickle
import os
from datetime import datetime

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")


def _path(key: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{today}_{key}.pkl")


def save(key: str, data) -> None:
    try:
        with open(_path(key), "wb") as f:
            pickle.dump(data, f)
    except Exception as e:
        print(f"[DiskCache] 保存失败 {key}: {e}")


def load(key: str):
    p = _path(key)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"[DiskCache] 读取失败 {key}: {e}")
        return None


def exists(key: str) -> bool:
    return os.path.exists(_path(key))
