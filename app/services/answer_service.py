from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from app.core.prompts import build_grounded_prompt, build_signal_prompt
from app.core.safety import RISK_NOTICE, assess_question, build_guarded_answer
from app.models.chat import AskResponse, SourceReference
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

if TYPE_CHECKING:
    from app.models.chat import ConversationTurn
    from app.models.signal import SignalContext


class AnswerService:
    def __init__(self, retrieval: RetrievalService, llm: LLMService) -> None:
        self._retrieval = retrieval
        self._llm = llm

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_contexts_and_sources(
        self, results: list
    ) -> tuple[list[str], list[SourceReference]]:
        contexts: list[str] = []
        sources: list[SourceReference] = []
        for chunk, score in results:
            locator = " / ".join(
                item for item in [chunk.document_title, chunk.chapter, chunk.section] if item
            )
            pages = (
                f"（第 {chunk.page_start}-{chunk.page_end} 页）"
                if chunk.page_start and chunk.page_end
                else ""
            )
            contexts.append(f"来源：{locator}{pages}\n内容：{chunk.content}")
            sources.append(
                SourceReference(
                    chunk_id=chunk.chunk_id,
                    knowledge_domain=chunk.knowledge_domain,
                    document_title=chunk.document_title,
                    chapter=chunk.chapter,
                    section=chunk.section,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    score=round(score, 4),
                )
            )
        return contexts, sources

    @staticmethod
    def _no_data_response() -> AskResponse:
        return AskResponse(
            answer=(
                "## 结论\n当前知识库未检索到足够相关的资料，无法可靠回答该问题。\n\n"
                "## 建议\n请补充相关交易书籍、系统说明或信号规则资料后再次提问。\n\n"
                f"## 风险提示\n{RISK_NOTICE}"
            ),
            sources=[],
            risk_notice=RISK_NOTICE,
        )

    # ------------------------------------------------------------------
    # Public: blocking
    # ------------------------------------------------------------------

    async def ask(
        self,
        question: str,
        domains: list[str] | None,
        top_k: int,
        signal: SignalContext | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> AskResponse:
        risk = assess_question(question, has_signal_context=signal is not None)
        if risk.blocked:
            return AskResponse(
                answer=build_guarded_answer(risk.reason),
                sources=[],
                risk_notice=RISK_NOTICE,
                boundary_triggered=True,
            )

        results = await self._retrieval.retrieve(question, domains, top_k)
        if not results:
            return self._no_data_response()

        contexts, sources = self._build_contexts_and_sources(results)
        user_prompt = (
            build_signal_prompt(question, contexts, signal)
            if signal
            else build_grounded_prompt(question, contexts)
        )
        answer = await self._llm.answer(user_prompt, history)
        return AskResponse(answer=answer, sources=sources, risk_notice=RISK_NOTICE)

    # ------------------------------------------------------------------
    # Public: streaming
    # ------------------------------------------------------------------

    async def ask_stream(
        self,
        question: str,
        domains: list[str] | None,
        top_k: int,
        signal: SignalContext | None = None,
        history: list[ConversationTurn] | None = None,
    ) -> AsyncIterator[dict]:
        risk = assess_question(question, has_signal_context=signal is not None)
        if risk.blocked:
            yield {"type": "answer", "content": build_guarded_answer(risk.reason), "boundary_triggered": True}
            yield {"type": "done", "risk_notice": RISK_NOTICE}
            return

        results = await self._retrieval.retrieve(question, domains, top_k)
        if not results:
            yield {
                "type": "answer",
                "content": (
                    "## 结论\n当前知识库未检索到足够相关的资料，无法可靠回答该问题。\n\n"
                    "## 建议\n请补充相关交易书籍、系统说明或信号规则资料后再次提问。\n\n"
                    f"## 风险提示\n{RISK_NOTICE}"
                ),
            }
            yield {"type": "done", "risk_notice": RISK_NOTICE}
            return

        contexts, sources = self._build_contexts_and_sources(results)
        user_prompt = (
            build_signal_prompt(question, contexts, signal)
            if signal
            else build_grounded_prompt(question, contexts)
        )

        async for token in self._llm.answer_stream(user_prompt, history):
            yield {"type": "token", "content": token}

        yield {"type": "sources", "sources": [s.model_dump() for s in sources]}
        yield {"type": "done", "risk_notice": RISK_NOTICE}
