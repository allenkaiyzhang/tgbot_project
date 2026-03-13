# Minimal Telegram Bot Suite

这是一个最小可用的 Telegram Bot 项目。

## 文件与依赖关系

- `main.py`
  - 项目主入口，默认启动 `telegram_bot.main`
- `telegram_bot.py`（应用层）
  - 依赖 `config.py`（配置）
  - 依赖 `llm_service.py`（`/askds`）
  - 依赖 `longbridge_service.py`（`/askstock`）
  - 依赖 `gmail_service.py`（结果通知邮件）
- `llm_service.py`（LLM 服务层）
  - 封装 DeepSeek 与 ChatGPT 兼容网关调用
- `longbridge_service.py`（LongBridge 服务层）
  - 封装行情/持仓查询与结果整理
- `gmail_service.py`（邮件服务层）
  - 封装 Gmail SMTP 发信
- `config.py`（配置中心）
  - 统一读取环境变量与 `.env`
  - 提供 LongBridge OAuth + fallback 配置构建
- `telegram_echo_demo.py`
  - 简单 Echo Bot 示例

## 主要函数关系

- Telegram 消息处理
  - `telegram_bot.process_message()`
  - -> `_handle_askds_reply()` -> `llm_service.get_deepseek_response()`
  - -> `_handle_askstock_reply()` -> `longbridge_service.get_inspected_quotes_text()`
- 邮件通知
  - `telegram_bot._maybe_send_function_email()`
  - -> `gmail_service.send_gmail()`
- LongBridge 鉴权回退
  - `longbridge_service.setup_*_context()`
  - -> `config.build_config_with_fallback()`
  - -> OAuth 失败时回退 `config.build_apikey_env_config()`

## 运行方式

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置 `.env`

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DEEPSEEK_API_KEY=your_deepseek_api_key
LONGBRIDGE_CLIENT_ID=your_longbridge_client_id

GMAIL_SENDER=your_account@gmail.com
GMAIL_APP_PASSWORD=your_16_digit_app_password
GMAIL_TO=to1@example.com,to2@example.com
GMAIL_CC=

CHATGPT_API_KEY=your_chatgpt_or_gateway_key
CHATGPT_BASE_URL=https://burn.hair/v1
CHATGPT_MODEL=gpt-5.2
```

3. 启动项目

```bash
python main.py
```

## 扩展说明

- 如果要给更多命令启用邮件通知，在 `telegram_bot.py` 的 `EMAIL_NOTIFY_FUNCTIONS` 中添加函数名。
- 如果要切换 LLM 提供方，可在 `llm_service.py` 中使用 `get_llm_response(provider=...)`。
