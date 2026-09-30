"""Invariants of the candidate-universe specification and its frozen versions."""

import json
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from equity_research.config import (
    FROZEN_UNIVERSE_VERSIONS,
    INITIAL_UNIVERSE_V1,
    INITIAL_UNIVERSE_V1_ID,
    UniverseSpec,
    load_yaml_config,
)

POSITIVE_FIELDS = [
    "min_price_usd",
    "liquidity_lookback_sessions",
    "min_median_dollar_volume_usd",
    "min_history_sessions",
    "max_constituents",
]
INTEGER_FIELDS = [
    "liquidity_lookback_sessions",
    "min_history_sessions",
    "max_constituents",
]


def _load(data: object) -> UniverseSpec:
    return load_yaml_config(json.dumps(data), UniverseSpec)


def _v1(**overrides: Any) -> dict[str, Any]:
    return {**INITIAL_UNIVERSE_V1.model_dump(mode="json"), **overrides}


def _experimental(**overrides: Any) -> dict[str, Any]:
    """V1 parameters under a non-frozen version id, so single rules can be varied."""
    return _v1(version="EXPERIMENTAL_TEST", **overrides)


def test_initial_universe_v1_matches_contract() -> None:
    assert INITIAL_UNIVERSE_V1.version == "INITIAL_UNIVERSE_V1"
    assert INITIAL_UNIVERSE_V1.min_price_usd == 5.0
    assert INITIAL_UNIVERSE_V1.liquidity_lookback_sessions == 60
    assert INITIAL_UNIVERSE_V1.min_median_dollar_volume_usd == 20_000_000.0
    assert INITIAL_UNIVERSE_V1.min_history_sessions == 252
    assert INITIAL_UNIVERSE_V1.max_constituents == 1000
    assert INITIAL_UNIVERSE_V1.eligibility_information == "point_in_time"
    assert set(INITIAL_UNIVERSE_V1.excluded_security_classes) == {
        "adr",
        "closed_end_fund",
        "etf_etp",
        "otc_only",
        "preferred",
        "right",
        "spac",
        "unit",
        "warrant",
    }


@given(field=st.sampled_from(POSITIVE_FIELDS), value=st.integers(max_value=0))
def test_zero_or_negative_thresholds_rejected(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        _load(_experimental(**{field: value}))


@given(
    field=st.sampled_from(["min_price_usd", "min_median_dollar_volume_usd"]),
    value=st.floats(max_value=0, allow_nan=False, allow_infinity=False),
)
def test_non_positive_usd_thresholds_rejected(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        _load(_experimental(**{field: value}))


@pytest.mark.parametrize("field", INTEGER_FIELDS)
@pytest.mark.parametrize("value", [60.0, 60.5, "60", True])
def test_session_and_count_fields_require_integers(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _load(_experimental(**{field: value}))


@given(
    lookback=st.integers(min_value=2, max_value=2_000),
    shortfall=st.integers(min_value=1, max_value=2_000),
)
def test_history_shorter_than_liquidity_lookback_rejected(lookback: int, shortfall: int) -> None:
    history = max(1, lookback - shortfall)
    with pytest.raises(ValidationError, match="min_history_sessions"):
        _load(_experimental(liquidity_lookback_sessions=lookback, min_history_sessions=history))


def test_duplicate_exclusions_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicates"):
        _load(_experimental(excluded_security_classes=["adr", "adr", "spac"]))


@given(order=st.permutations(list(INITIAL_UNIVERSE_V1.excluded_security_classes)))
def test_exclusion_order_is_canonicalized(order: list[str]) -> None:
    assert _load(_v1(excluded_security_classes=order)) == INITIAL_UNIVERSE_V1


def test_unknown_security_class_rejected() -> None:
    with pytest.raises(ValidationError):
        _load(_experimental(excluded_security_classes=["adr", "bitcoin_trust"]))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("min_price_usd", 1.0),
        ("liquidity_lookback_sessions", 20),
        ("min_median_dollar_volume_usd", 10_000_000.0),
        ("min_history_sessions", 504),
        ("max_constituents", 500),
        ("excluded_security_classes", ["etf_etp", "spac"]),
    ],
)
def test_frozen_version_cannot_be_redefined(field: str, value: object) -> None:
    with pytest.raises(ValidationError, match="frozen universe version"):
        _load(_v1(**{field: value}))
    # The same rule change is representable under a new version identifier.
    assert _load(_experimental(**{field: value})).version == "EXPERIMENTAL_TEST"


def test_every_frozen_version_validates() -> None:
    for version, params in FROZEN_UNIVERSE_VERSIONS.items():
        assert _load({"version": version, **params}).version == version
    assert INITIAL_UNIVERSE_V1_ID in FROZEN_UNIVERSE_VERSIONS


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("eligibility_information", "current_membership"),
        ("security_type", "any_equity"),
        ("listing_scope", "otc"),
    ],
)
def test_non_point_in_time_or_broader_scopes_not_representable(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        _load(_experimental(**{field: value}))
