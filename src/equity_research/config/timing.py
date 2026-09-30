"""Signal / execution timing, rebalance rule and primary-target definition.

See ``docs/time_and_execution_contract.md`` and ``docs/research_contract.md``.
"""

from typing import Literal

from equity_research.config._base import FrozenModel, PositiveSessions

MARKET_TIMEZONE = "America/New_York"


class TimingConvention(FrozenModel):
    """When a signal may be formed and when it may first be acted on.

    Only one convention is representable in Phase 1. In particular there is no value
    for same-bar or same-close execution.
    """

    market_timezone: Literal["America/New_York"]
    signal_time: Literal["after_regular_close"]
    execution_time: Literal["next_regular_session_open"]


class RebalanceRule(FrozenModel):
    frequency: Literal["weekly"]
    signal_session: Literal["final_regular_session_of_week"]


class PrimaryTargetSpec(FrozenModel):
    """Definition (not implementation) of the Phase-1 primary prediction target.

    Cross-sectional percentile rank of total return from the executable next open
    to the open ``horizon_sessions`` regular sessions later. The horizon is fixed in
    regular sessions; it is never redefined as "until the next rebalance", which can
    differ around holidays (see ``docs/time_and_execution_contract.md``). Market, beta- or
    sector-relative variants are separate hypotheses and are not representable here.
    """

    horizon_sessions: PositiveSessions
    return_measure: Literal["total_return"]
    entry_price: Literal["execution_session_open"]
    exit_price: Literal["open_after_horizon_sessions"]
    cross_sectional_transform: Literal["percentile_rank"]
