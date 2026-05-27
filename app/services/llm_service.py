from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.prompts import SYSTEM_PROMPT


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    async def answer(self, user_prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            temperature=self._settings.llm_temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or "当前未生成有效回答。"
