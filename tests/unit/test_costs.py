"""Invariants of the transaction-cost scenario model."""

import json
import math
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from equity_research.config import TransactionCostModel, load_yaml_config


def _load(data: object) -> TransactionCostModel:
    return load_yaml_config(json.dumps(data), TransactionCostModel)


def _model(*scenarios: tuple[str, str, float]) -> dict[str, Any]:
    return {
        "basis": "one_way_traded_notional",
        "scenarios": [{"name": n, "role": r, "one_way_bps": b} for n, r, b in scenarios],
    }


VALID = _model(("base", "base", 10.0), ("stress", "stress", 20.0), ("zero", "diagnostic", 0.0))


def test_phase1_cost_scenarios_validate() -> None:
    _load(VALID)


@given(
    bps=st.floats(max_value=0, exclude_max=True, allow_nan=False, allow_infinity=False),
    role=st.sampled_from(["base", "stress", "diagnostic"]),
)
def test_negative_cost_is_rejected_for_every_role(bps: float, role: str) -> None:
    data = _model(("base", "base", 10.0), ("stress", "stress", 20.0), ("x", role, bps))
    with pytest.raises(ValidationError):
        _load(data)


@pytest.mark.parametrize("bps", [math.nan, math.inf, 10_000.01, "10", True])
def test_non_finite_out_of_range_or_non_numeric_cost_is_rejected(bps: object) -> None:
    data = _model(("stress", "stress", 20.0))
    data["scenarios"].append({"name": "base", "role": "base", "one_way_bps": bps})
    with pytest.raises(ValidationError):
        _load(data)


@pytest.mark.parametrize(
    "data",
    [
        _model(("zero", "base", 0.0), ("stress", "stress", 20.0)),
        _model(("base", "base", 10.0), ("stress", "stress", 20.0), ("zero", "stress", 0.0)),
    ],
    ids=["zero-as-base", "zero-as-stress"],
)
def test_zero_cost_is_diagnostic_only(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="diagnostic"):
        _load(data)


def test_exactly_one_base_scenario_required() -> None:
    with pytest.raises(ValidationError, match="exactly one base"):
        _load(_model(("stress", "stress", 20.0)))
    with pytest.raises(ValidationError, match="exactly one base"):
        _load(_model(("a", "base", 10.0), ("b", "base", 12.0), ("s", "stress", 20.0)))


def test_stress_scenario_required() -> None:
    with pytest.raises(ValidationError, match="stress"):
        _load(_model(("base", "base", 10.0)))


def test_duplicate_scenario_names_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        _load(_model(("base", "base", 10.0), ("base", "stress", 20.0)))


@given(
    base=st.floats(min_value=0.01, max_value=500, allow_nan=False),
    extra=st.floats(min_value=0.01, max_value=500, allow_nan=False),
)
def test_stress_below_base_rejected_and_at_or_above_base_accepted(
    base: float, extra: float
) -> None:
    with pytest.raises(ValidationError, match="cheaper than base"):
        _load(_model(("base", "base", base + extra), ("stress", "stress", base)))
    model = _load(_model(("base", "base", base), ("stress", "stress", base + extra)))
    assert _load(model.model_dump(mode="json")) == model
