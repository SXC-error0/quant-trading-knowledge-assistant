from app.core.safety import assess_question, build_guarded_answer


def test_blocks_specific_instant_trade_decision() -> None:
    result = assess_question("BTC 现在能买吗？")
    assert result.blocked is True


def test_blocks_extreme_leverage_request() -> None:
    result = assess_question("我想全仓开 50 倍杠杆做多 BTCUSDT，可以吗？")
    assert result.blocked is True


def test_allows_indicator_education_question() -> None:
    result = assess_question("MACD 金叉是否可以作为买入依据？")
    assert result.blocked is False


def test_allows_risk_management_concept_question() -> None:
    result = assess_question("短线交易中应该如何理解止损？")
    assert result.blocked is False


def test_guarded_answer_has_non_advisory_boundary() -> None:
    answer = build_guarded_answer("请求涉及即时交易决策")
    assert "无法直接给出确定性的买入" in answer
    assert "不构成" in answer
