# Please install OpenAI SDK first: `pip install openai`
"""DeepSeek API 封装层：对外只暴露一个文本问答函数。"""

from openai import OpenAI

import config


# 复用全局 client，避免每次请求都新建连接对象。
client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)


def get_deepseek_response(prompt: str) -> str:
    """调用 deepseek-chat 并返回纯文本回复。"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )

    return response.choices[0].message.content
