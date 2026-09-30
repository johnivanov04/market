"""Invariants of timing, rebalance and primary-target definitions."""

import json
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from equity_research.config import (
    MARKET_TIMEZONE,
    PrimaryTargetSpec,
    TimingConvention,
    load_yaml_config,
)

TIMING: dict[str, Any] = {
    "market_timezone": "America/New_York",
    "signal_time": "after_regular_close",
    "execution_time": "next_regular_session_open",
}
TARGET: dict[str, Any] = {
    "horizon_sessions": 5,
    "return_measure": "total_return",
    "entry_price": "execution_session_open",
    "exit_price": "open_after_horizon_sessions",
    "cross_sectional_transform": "percentile_rank",
}


def test_market_timezone_is_a_resolvable_iana_zone() -> None:
    assert ZoneInfo(MARKET_TIMEZONE).key == "America/New_York"


@given(horizon=st.integers(max_value=0))
def test_zero_or_negative_horizon_rejected(horizon: int) -> None:
    with pytest.raises(ValidationError):
        load_yaml_config(json.dumps({**TARGET, "horizon_sessions": horizon}), PrimaryTargetSpec)


@pytest.mark.parametrize("horizon", [5.0, 5.5, "5", True])
def test_non_integer_horizon_rejected(horizon: object) -> None:
    with pytest.raises(ValidationError):
        load_yaml_config(json.dumps({**TARGET, "horizon_sessions": horizon}), PrimaryTargetSpec)


@pytest.mark.parametrize(
    "execution_time",
    ["same_close", "signal_session_close", "same_bar", "signal_session_open", "next_close"],
)
def test_same_close_and_other_executions_not_representable(execution_time: str) -> None:
    with pytest.raises(ValidationError):
        load_yaml_config(json.dumps({**TIMING, "execution_time": execution_time}), TimingConvention)


@given(value=st.text().filter(lambda s: s != "next_regular_session_open"))
def test_only_next_open_execution_is_accepted(value: str) -> None:
    with pytest.raises(ValidationError):
        load_yaml_config(json.dumps({**TIMING, "execution_time": value}), TimingConvention)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("market_timezone", "UTC"),
        ("market_timezone", "US/Eastern"),
        ("signal_time", "intraday"),
    ],
)
def test_alternative_timing_conventions_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        load_yaml_config(json.dumps({**TIMING, field: value}), TimingConvention)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("return_measure", "excess_return"),
        ("return_measure", "beta_residual_return"),
        ("return_measure", "sector_relative_return"),
        ("entry_price", "signal_session_close"),
        ("cross_sectional_transform", "raw"),
    ],
)
def test_secondary_or_same_close_target_variants_not_representable(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        load_yaml_config(json.dumps({**TARGET, field: value}), PrimaryTargetSpec)
