# Telegram Bot Suite

Minimal Telegram bot project with:
- `askds` (DeepSeek)
- `askchatgpt` (ChatGPT/OpenAI-compatible endpoint)
- `askstock` (LongBridge quote query)
- optional Gmail notification per command (with response attachment)

## Architecture

- [main.py](/d:/tgbot/main.py)
  - startup entrypoint
  - calls `telegram_bot.main()`
- [telegram_bot.py](/d:/tgbot/telegram_bot.py)
  - Telegram command registration
  - delegates business flow to `bot_flow`
- [bot_flow.py](/d:/tgbot/bot_flow.py)
  - stateful `BotFlow` class
  - manages pending chat states
  - command execution and email notification
  - `askstock` includes second-step confirmation:
    - asks: `Need advanced technical analysis by ChatGPT? (yes/no)`
    - if reply is `yes`, calls ChatGPT for technical analysis
- [ai_notification_service.py](/d:/tgbot/ai_notification_service.py)
  - merged AI + email service module
  - LLM API: `get_llm_response(...)`
  - Email API: `send_gmail(...)`
- [longbridge_service.py](/d:/tgbot/longbridge_service.py)
  - `LB` class for LongBridge quote/trade/news capabilities
  - wrapper API used by bot: `get_inspected_quotes_text(...)`
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
  - calls `ai_notification_service.get_llm_response(provider="deepseek")`
- `/askchatgpt`
  - waits for next message
  - calls `ai_notification_service.get_llm_response(provider="chatgpt")`
- `/askstock`
  - waits for stock symbols
  - calls `longbridge_service.get_inspected_quotes_text(...)`
  - returns market snapshot data including:
    - realtime quote
    - candlesticks
    - history candlesticks by offset
  - asks yes/no for advanced analysis
  - if yes, calls ChatGPT with date + stock response context

## Email Notification

- Configured in `bot_flow` by `email_notify_functions`
- Sends only when response is non-empty
- Each email includes:
  - summary body (DeepSeek-generated concise summary + success/non-empty flags)
  - request attachment (`.txt`)
  - response attachment (`.txt`)

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

## Notes

- Do not commit real API keys/tokens.
- `askstock` advanced analysis may increase ChatGPT latency and cost when quote payloads are large.
- Standalone echo test script is at `test/telegram_echo_demo.py` (kept independent from project modules).
