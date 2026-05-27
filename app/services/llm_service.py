from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.prompts import build_messages

if TYPE_CHECKING:
    from app.models.chat import ConversationTurn


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    async def answer(
        self,
        user_prompt: str,
        history: list[ConversationTurn] | None = None,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            temperature=self._settings.llm_temperature,
            messages=build_messages(user_prompt, history),
        )
        return response.choices[0].message.content or "当前未生成有效回答。"

    async def answer_stream(
        self,
        user_prompt: str,
        history: list[ConversationTurn] | None = None,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._settings.llm_model,
            temperature=self._settings.llm_temperature,
            messages=build_messages(user_prompt, history),
            stream=True,
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token
