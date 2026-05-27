from typing import Literal

from pydantic import BaseModel, Field


class SignalContext(BaseModel):
    """Trading signal emitted by the market-watching system.

    When provided, the assistant may explain and analyse the signal instead of
    refusing questions that would normally be blocked as direct trade decisions.
    Extreme-risk requests (all-in, guaranteed-profit) are still blocked.
    """

    signal_type: Literal["buy", "sell", "close", "warning"]
    asset: str = Field(min_length=1, max_length=30, examples=["BTCUSDT"])
    strategy_name: str | None = Field(default=None, max_length=100)
    conditions_met: list[str] = Field(
        default_factory=list,
        description="Human-readable list of conditions that triggered the signal.",
    )
    triggered_at: str | None = Field(
        default=None,
        description="ISO-8601 timestamp when the signal fired.",
    )
    timeframe: str | None = Field(default=None, max_length=10, examples=["1h", "4h", "1d"])
