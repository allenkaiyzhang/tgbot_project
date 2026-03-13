# Minimal Telegram Bot Suite

这是一个最小可用的 Telegram Bot 项目。

## 文件结构

- `main.py`：统一主启动入口（默认启动 Telegram Bot）
- `telegram_bot.py`：主 Bot 逻辑（`/askds`、`/askstock`、邮件通知）
- `deepseek_service.py`：DeepSeek 调用封装
- `longbridge_service.py`：LongBridge 行情/持仓相关功能
- `gmail_service.py`：Gmail 发信工具
- `config.py`：项目配置中心（环境变量读取 + LongBridge 配置构建与回退）
- `telegram_echo_demo.py`：Echo Bot 示例

## 运行方式

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置 `.env`

```env
TELEGRAM_BOT_TOKEN=你的telegram_bot_token
DEEPSEEK_API_KEY=你的deepseek_api_key
LONGBRIDGE_CLIENT_ID=你的longbridge_client_id

GMAIL_SENDER=your_account@gmail.com
GMAIL_APP_PASSWORD=your_16_digit_app_password
GMAIL_TO=to1@example.com,to2@example.com
GMAIL_CC=
```

3. 启动项目

```bash
python main.py
```

## 功能说明

- `/askds`：输入 prompt，返回 DeepSeek 回复
- `/askstock`：输入股票代码（支持空格/逗号分隔多个），返回 LongBridge 行情信息
- 邮件通知：`askds/askstock` 返回非空结果时自动通知默认收件人

## 扩展说明

- 若要给更多函数加邮件通知，在 `telegram_bot.py` 的 `EMAIL_NOTIFY_FUNCTIONS` 中增加函数名即可。
