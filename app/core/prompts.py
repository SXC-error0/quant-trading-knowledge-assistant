from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.chat import ConversationTurn
    from app.models.signal import SignalContext

SYSTEM_PROMPT = """你是看盘工具中的"量化交易专业知识助手"。

你的职责：
1. 仅基于提供的知识片段，解释量化交易、短线策略、技术指标、回测评估、风险管理和系统操作问题。
2. 核心结论应与引用来源对应；没有足够资料时，明确说明当前知识库依据不足。
3. 不得将策略、指标或系统提醒表述为保证盈利的即时交易指令。
4. 不得承诺收益、保证胜率、鼓励全仓/重仓/高杠杆或暗示能够预测未来价格。
5. 不暴露内部思考过程，不复现大段版权原文，优先进行概括和解释。

回答结构：
## 结论
## 原理解释
## 使用注意
## 与本系统的关系（仅在问题涉及系统功能或提醒时输出）
## 参考来源
## 风险提示
"""

_RISK_NOTICE = (
    "本回答用于解释交易知识与系统规则，不构成对具体数字资产当前时点的"
    "确定性买卖建议、收益承诺或投资保证。"
)


def build_grounded_prompt(question: str, contexts: list[str]) -> str:
    joined = "\n\n---\n\n".join(contexts)
    return (
        f"请回答用户问题。\n\n"
        f"用户问题：\n{question}\n\n"
        f"可用知识片段：\n{joined}\n\n"
        "要求：\n"
        "- 只能依据以上片段给出专业结论；资料未覆盖的内容应说明不足。\n"
        "- 参考来源部分只列出知识片段中确实出现的来源。\n"
        "- 不大段照录原文。\n"
    )


def build_signal_prompt(question: str, contexts: list[str], signal: SignalContext) -> str:
    _SIGNAL_TYPE_LABEL = {
        "buy": "买入信号",
        "sell": "卖出信号",
        "close": "平仓信号",
        "warning": "风险预警",
    }
    label = _SIGNAL_TYPE_LABEL.get(signal.signal_type, signal.signal_type)
    conditions = "\n".join(f"  - {c}" for c in signal.conditions_met) or "  （未提供）"
    signal_block = (
        f"【系统当前信号】\n"
        f"- 信号类型：{label}\n"
        f"- 标的：{signal.asset}\n"
        f"- 策略：{signal.strategy_name or '未指定'}\n"
        f"- 周期：{signal.timeframe or '未指定'}\n"
        f"- 触发条件：\n{conditions}\n"
        f"- 触发时间：{signal.triggered_at or '未指定'}\n"
    )

    joined = "\n\n---\n\n".join(contexts)
    return (
        f"{signal_block}\n"
        f"用户问题：\n{question}\n\n"
        f"可用知识片段：\n{joined}\n\n"
        "要求：\n"
        "- 结合上方系统信号和知识片段，解释该信号的含义、触发逻辑与适用条件。\n"
        "- 说明用户在此信号下应关注的风险点和使用注意事项。\n"
        "- 不得保证该信号必然盈利，不得鼓励全仓或极端仓位。\n"
        "- 参考来源只列实际出现的片段来源。\n"
    )


def build_messages(
    user_prompt: str,
    history: list[ConversationTurn] | None = None,
) -> list[dict[str, str]]:
    """Assemble the full messages list including optional conversation history."""
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history or []:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": user_prompt})
    return messages
