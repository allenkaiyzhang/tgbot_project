# Please install OpenAI SDK first: `pip install openai`

from openai import OpenAI

import config


client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)


def get_deepseek_response(prompt: str) -> str:
    """Use deepseek-chat to generate a response for the given prompt."""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )

    return response.choices[0].message.content
