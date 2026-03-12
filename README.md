# Minimal Telegram Bot Suite

这是一个最小可用的 Telegram Bot 项目示例，包含：

- `bot.py`：最简 Telegram Bot，实现 `/askds` 调用 DeepSeek Chat、`/askstock` 查询行情、其他消息统一回复 `1`。
- `deepseek_client.py`：封装 DeepSeek Chat 调用，返回 `response.choices[0].message.content`。
- `quote_status.py`：负责从 Longbridge SDK 获取行情并格式化输出。
- 其它测试脚本（`order_test.py`、`longbridge_sdk_test.py`）用于验证 SDK 行为。

## 运行方式
1. 安装依赖：`pip install pyTelegramBotAPI openai`
2. 配置 token/key（推荐方式：使用 `.env` 文件）：
   - 复制 `.env` 为 `.env`（若不存在）并填入真实值：
     - `TELEGRAM_BOT_TOKEN=你的token`
     - `DEEPSEEK_API_KEY=你的key`
     - `LONGBRIDGE_CLIENT_ID=你的client_id`
   - 也可按需使用环境变量覆盖：
     - `export TELEGRAM_BOT_TOKEN=你的token`
     - `export DEEPSEEK_API_KEY=你的key`
     - `export LONGBRIDGE_CLIENT_ID=你的client_id`
3. 运行：`python bot.py`

### Bot 功能
- `/askds`：提示输入 prompt，发送后返回 DeepSeek Chat 的回复
- `/askstock`：提示输入股票代码，发送后返回 Longbridge 获取的行情信息
- 其他消息：统一回复 `1`
