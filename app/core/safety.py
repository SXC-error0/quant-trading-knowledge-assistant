import re
from dataclasses import dataclass

RISK_NOTICE = (
    "本回答用于解释交易知识与系统规则，不构成对具体数字资产当前时点的"
    "确定性买卖建议、收益承诺或投资保证。"
)

_DIRECT_DECISION_PATTERNS = (
    r"(现在|马上|立刻|今天|此刻|当前).{0,30}(买|卖|做多|做空|入场|开仓|加仓)",
    r"(btc|eth|bnb|sol|xrp|doge|usdt|比特币|以太坊).{0,30}"
    r"(能买吗|能卖吗|买还是卖|做多|做空|入场|开仓|加仓)",
    r"[a-z0-9]{2,12}usdt.{0,30}(能买吗|能卖吗|买还是卖|做多|做空|入场|开仓|加仓)",
)
_EXTREME_RISK_PATTERNS = (
    r"(全仓|梭哈|满仓|重仓)",
    r"([2-9][0-9]|[1-9][0-9]{2,})\s*倍.*(杠杆|做多|做空|开仓)",
    r"(保证|稳赚|必赚|一定盈利|百分百|胜率\s*100)",
)


@dataclass(frozen=True)
class RiskAssessment:
    blocked: bool
    reason: str | None = None


def assess_question(question: str) -> RiskAssessment:
    """Identify requests that require a constrained non-advisory response."""
    normalized = question.strip().lower()
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _EXTREME_RISK_PATTERNS):
        return RiskAssessment(True, "请求涉及极端风险操作或收益保证")
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _DIRECT_DECISION_PATTERNS):
        return RiskAssessment(True, "请求要求针对具体资产作出即时买卖决策")
    return RiskAssessment(False)


def build_guarded_answer(reason: str | None) -> str:
    detail = reason or "问题超出知识解释范围"
    return (
        f"## 结论\n当前无法直接给出确定性的买入、卖出或仓位建议。原因：{detail}。\n\n"
        "## 可提供的帮助\n"
        "我可以解释相关指标、策略条件、止损与仓位管理原理，或说明系统中某条提醒的含义。"
        "若需要理解一条已产生的系统提醒，请提供该信号的策略规则与触发依据。\n\n"
        "## 风险提示\n"
        f"{RISK_NOTICE}"
    )
