# TODO / 待办

## 优化建议（非必需）

- ✅ 将 `BOT_TOKEN` 从代码中移动到环境变量（如 `TELEGRAM_BOT_TOKEN`），避免泄露。
- ✅ 为 `/askds`、`/askstock` 加超时机制：如果用户长时间不回复，则退出等待状态。
- ➕ 增加错误处理：当 DeepSeek 或 Longbridge 接口报错时，友好提示并不让程序崩溃。
- ➕ 支持 `@botname` 在群组中触发命令（例如 `@yourbot /askstock`）。
- ➕ 在 `test_status.py` 中对行情数据做更多字段过滤，避免输出过多无用内容。
