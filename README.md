# Minimal Telegram Bot Suite

这是一个最小可用的 Telegram Bot 项目。

## 文件与依赖关系

- `main.py`
  - 项目主入口，默认启动 `telegram_bot.main`
- `telegram_bot.py`（入口层）
  - 负责 Telegram 命令注册和路由
  - 将业务处理委托给 `bot_flow.py`
- `bot_flow.py`（会话与业务流层）
  - 管理 `askds / askchatgpt / askstock` 的等待状态
  - 调用 `llm_service.py`、`longbridge_service.py`、`gmail_service.py`
- `llm_service.py`（LLM 服务层）
  - 提供统一函数 `get_llm_response(...)`
  - 支持 `deepseek` 与 `chatgpt/openai` provider
- `longbridge_service.py`（LongBridge 服务层）
  - 提供行情与持仓查询能力
- `gmail_service.py`（邮件服务层）
  - 提供 Gmail SMTP 发信能力
- `config.py`（配置中心）
  - 统一读取环境变量与 `.env`
  - 提供 LongBridge OAuth + fallback 配置构建
- `telegram_echo_demo.py`
  - 简易 Echo Bot 示例

## 主要函数关系

- Telegram 消息处理
  - `telegram_bot.handle_echo()`
  - -> `bot_flow.process_message()`
  - -> `_handle_askds_reply()` -> `llm_service.get_llm_response(provider="deepseek")`
  - -> `_handle_askchatgpt_reply()` -> `llm_service.get_llm_response(provider="chatgpt")`
  - -> `_handle_askstock_reply()` -> `longbridge_service.get_inspected_quotes_text()`
- 邮件通知
  - `bot_flow._maybe_send_function_email()`
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

- 要给更多命令加邮件通知，在 `bot_flow.py` 的 `EMAIL_NOTIFY_FUNCTIONS` 中增加函数名。
- 要切换 LLM 提供方，使用 `llm_service.get_llm_response(provider=...)`。
