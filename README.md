# Telegram Bot Suite

Minimal Telegram bot project with:
- `askds` (DeepSeek)
- `askchatgpt` (ChatGPT/OpenAI-compatible endpoint)
- `askstock` (LongBridge quote query)
- optional Gmail notification per command (with response attachment)

## Architecture

- [main.py](/d:/tgbot/main.py)
  - startup entrypoint
  - calls `bot.telegram_bot.main()`
- [bot/telegram_bot.py](/d:/tgbot/bot/telegram_bot.py)
  - Telegram command registration
  - delegates business flow to `bot_flow`
- [bot/bot_flow.py](/d:/tgbot/bot/bot_flow.py)
  - stateful `BotFlow` class
  - manages pending chat states
  - command execution and email notification
  - `askstock` includes second-step confirmation:
    - asks: `Need advanced technical analysis by ChatGPT? (yes/no)`
    - if reply is `yes`, calls ChatGPT for technical analysis
- [services/ai_notification_service.py](/d:/tgbot/services/ai_notification_service.py)
  - merged AI + email service module
  - LLM API: `get_llm_response(...)`
  - Email API: `send_gmail(...)`
  - unified result APIs: `get_llm_response_result(...)`, `send_gmail_result(...)`
- [services/longbridge_service.py](/d:/tgbot/services/longbridge_service.py)
  - `LB` facade class for LongBridge quote/trade capabilities
  - wrapper API used by bot: `get_inspected_quotes_text(...)`
  - unified result API: `get_inspected_quotes_result(...)`
- [services/longbridge_quote_service.py](/d:/tgbot/services/longbridge_quote_service.py)
  - quote domain service + askstock snapshot builders
- [services/longbridge_trade_service.py](/d:/tgbot/services/longbridge_trade_service.py)
  - trade domain service
- [services/service_result.py](/d:/tgbot/services/service_result.py)
  - shared `ServiceResult` model (`ok/data/error_code/error_msg`)
- [config.py](/d:/tgbot/config.py)
  - unified env + `.env` loader
  - shared fixed-text loader from `app_texts.json`
  - LongBridge OAuth + API-key fallback config
- [app_texts.json](/d:/tgbot/app_texts.json)
  - centralized fixed prompts/messages/templates
  - update this file to adjust bot copywriting without touching Python logic
  - required at runtime; startup will fail if this file is missing

## Command Flow

- `/askds`
  - waits for next message
  - calls `ai_notification_service.get_llm_response_result(provider="deepseek")`
- `/askchatgpt`
  - waits for next message
  - calls `ai_notification_service.get_llm_response_result(provider="chatgpt")`
- `/askstock`
  - waits for stock symbols
  - returns realtime quote + candlesticks + offset candlesticks
  - if response text is longer than 4000 chars, bot sends a `.txt` file instead
  - asks yes/no for advanced analysis
  - if yes, calls ChatGPT with date + stock response context

## Email Notification

- Configured in `bot_flow` by `email_notify_functions`
- Sends only on failed query handling
- Each email includes:
  - summary body (failure context)
  - one detailed query log attachment (`.txt`)

## Query Logging

- Every query is persisted under `log/`
- `log/query_index.csv` stores per-query summary/index
- Detailed request/response content is saved as categorized text files under `log/<category>/`
- `askds` forces tokenizer-based token counting and records it; if tokenizer is unavailable, value is `-1`.
- If `tools/deepseek_v3_tokenizer` and `transformers` are available, token counts are also recorded.
  - DeepSeek calls: token count is accurate by DeepSeek tokenizer.
  - ChatGPT/OpenAI calls: token count is approximate (still using DeepSeek tokenizer).

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure `.env`:

```env
TELEGRAM_BOT_TOKEN=...

DEEPSEEK_API_KEY=...
CHATGPT_API_KEY=...
CHATGPT_BASE_URL=https://burn.hair/v1
CHATGPT_MODEL=gpt-5.2

LONGBRIDGE_CLIENT_ID=...
LONGBRIDGE_APP_KEY=...
LONGBRIDGE_APP_SECRET=...
LONGBRIDGE_ACCESS_TOKEN=...
LONGBRIDGE_PRINT_QUOTE_PACKAGES=false

GMAIL_SENDER=...
GMAIL_APP_PASSWORD=...
GMAIL_TO=...
GMAIL_CC=
```

3. Run:

```bash
python main.py
```

Startup now includes a preflight check:
- blocks startup on missing required env keys or app_texts keys
- logs warnings for optional/partial configuration

## Notes

- Do not commit real API keys/tokens.
- `askstock` advanced analysis may increase ChatGPT latency and cost when quote payloads are large.
- Standalone echo test script is at `test/telegram_echo_demo.py` (kept independent from project modules).
- Minimal unit tests are in `tests/` (`python -m unittest discover -s tests -p "test_*.py"`).

