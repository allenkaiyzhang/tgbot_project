"""配置文件：统一管理本地 token/密钥等配置。

推荐方式（优先级高到低）：
1) 环境变量（例如：`export TELEGRAM_BOT_TOKEN=...`）
2) 项目根目录 `.env` 文件
3) 本文件内的默认占位符（仅作提示）

使用 `.env` 可以避免将 token 直接写在代码里，同时也无需每次手动设置环境变量。
"""

import os


def _load_dotenv(path=".env") -> dict:
    """从 .env 文件加载键值对。

    支持格式：KEY=VALUE，忽略注释和空行。
    """

    if not os.path.exists(path):
        return {}

    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            env[key] = val
    return env


# ① 默认值（仅作占位和提示）
_DEFAULT_TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
_DEFAULT_DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"
_DEFAULT_LONGBRIDGE_CLIENT_ID = "YOUR_LONGBRIDGE_CLIENT_ID"

# ② 读取 .env 文件（如果存在）
_dotenv = _load_dotenv(".env")

# ③ 读取环境变量（优先）-> .env -> 默认值
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", _dotenv.get("TELEGRAM_BOT_TOKEN", _DEFAULT_TELEGRAM_BOT_TOKEN))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", _dotenv.get("DEEPSEEK_API_KEY", _DEFAULT_DEEPSEEK_API_KEY))
LONGBRIDGE_CLIENT_ID = os.getenv("LONGBRIDGE_CLIENT_ID", _dotenv.get("LONGBRIDGE_CLIENT_ID", _DEFAULT_LONGBRIDGE_CLIENT_ID))

# 默认查询股票列表（如果不传 symbols，会使用这里）
DEFAULT_SYMBOLS = ["VIX.US"]
