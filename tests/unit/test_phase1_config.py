"""The canonical Phase-1 configuration and the loader's determinism/strictness guarantees.

These tests establish configuration invariants only. They say nothing about the
correctness of any market data.
"""

import json
import random
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from equity_research.config import (
    INITIAL_UNIVERSE_V1,
    ConfigSyntaxError,
    FinalHoldout,
    Phase1Config,
    canonical_json,
    config_hash,
    dump_yaml_config,
    load_phase1_config,
    load_yaml_config,
)

BASE_YAML = Path(__file__).resolve().parents[2] / "configs" / "phase1" / "base.yaml"
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _base_data() -> dict[str, Any]:
    return yaml.safe_load(BASE_YAML.read_text(encoding="utf-8"))


def _load(data: object) -> Phase1Config:
    return load_yaml_config(json.dumps(data), Phase1Config)


def test_canonical_phase1_yaml_validates() -> None:
    assert isinstance(load_phase1_config(BASE_YAML), Phase1Config)


def test_canonical_phase1_yaml_encodes_the_frozen_contract() -> None:
    cfg = load_phase1_config(BASE_YAML)
    assert cfg.timing.market_timezone == "America/New_York"
    assert cfg.timing.signal_time == "after_regular_close"
    assert cfg.timing.execution_time == "next_regular_session_open"
    assert cfg.rebalance.frequency == "weekly"
    assert cfg.rebalance.signal_session == "final_regular_session_of_week"
    assert cfg.primary_target.horizon_sessions == 5
    assert cfg.primary_target.cross_sectional_transform == "percentile_rank"
    assert cfg.portfolio.long_only is True
    assert cfg.portfolio.max_gross_exposure == 1.0
    assert cfg.universe == INITIAL_UNIVERSE_V1
    costs = {s.name: (s.role, s.one_way_bps) for s in cfg.transaction_costs.scenarios}
    assert costs == {
        "base": ("base", 10.0),
        "stress": ("stress", 20.0),
        "zero_cost": ("diagnostic", 0.0),
    }
    assert cfg.transaction_costs.basis == "one_way_traded_notional"
    assert cfg.final_holdout.status == "unset"
    assert cfg.final_holdout.interval is None
    assert cfg.final_holdout.frozen_on is None
    assert "data-coverage audit" in cfg.final_holdout.reason


def test_loading_is_deterministic() -> None:
    first, second = load_phase1_config(BASE_YAML), load_phase1_config(BASE_YAML)
    assert first == second
    assert canonical_json(first) == canonical_json(second)


# --- config hash properties --------------------------------------------------------------
# The hash is not pinned to a literal digest: the frozen *values* are pinned above, and
# the properties below are what provenance actually relies on.


def _shuffle_keys(value: Any, rnd: random.Random) -> Any:
    if isinstance(value, dict):
        items: list[tuple[str, Any]] = list(value.items())  # pyright: ignore[reportUnknownArgumentType]
        rnd.shuffle(items)
        return {k: _shuffle_keys(v, rnd) for k, v in items}
    if isinstance(value, list):
        return [_shuffle_keys(v, rnd) for v in value]  # pyright: ignore[reportUnknownVariableType]
    return value


def test_config_hash_is_lowercase_sha256_hex() -> None:
    cfg = load_phase1_config(BASE_YAML)
    digest = config_hash(cfg)
    assert SHA256_HEX.fullmatch(digest)
    assert config_hash(cfg.universe) != digest
    assert SHA256_HEX.fullmatch(config_hash(cfg.universe))


def test_identical_semantic_config_has_identical_hash() -> None:
    from_file = load_phase1_config(BASE_YAML)
    from_other_load = load_phase1_config(BASE_YAML)
    from_json = Phase1Config.model_validate_json(json.dumps(_base_data()))
    assert config_hash(from_file) == config_hash(from_other_load) == config_hash(from_json)


@given(
    rnd=st.randoms(use_true_random=False),
    flow=st.sampled_from([False, True, None]),
    indent=st.integers(min_value=2, max_value=8),
    sort_keys=st.booleans(),
)
def test_hash_is_independent_of_yaml_key_order_and_formatting(
    rnd: random.Random, flow: bool | None, indent: int, sort_keys: bool
) -> None:
    text = yaml.safe_dump(
        _shuffle_keys(_base_data(), rnd),
        sort_keys=sort_keys,
        default_flow_style=flow,
        indent=indent,
        width=rnd.choice([40, 80, 10_000]),
    )
    # Comments and surrounding blank lines only; blank lines *inside* a document can be
    # semantic (a blank line within a wrapped scalar is a newline in the value).
    text = "# leading comment\n\n" + text + "\n# trailing comment\n"
    reformatted = load_yaml_config(text, Phase1Config)
    assert config_hash(reformatted) == config_hash(load_phase1_config(BASE_YAML))


def _set(path: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def edit(data: dict[str, Any]) -> None:
        *parents, leaf = path.split(".")
        node: Any = data
        for part in parents:
            node = node[int(part)] if part.isdigit() else node[part]
        node[int(leaf) if leaf.isdigit() else leaf] = value

    return edit


SEMANTIC_EDITS: dict[str, list[Callable[[dict[str, Any]], None]]] = {
    "horizon": [_set("primary_target.horizon_sessions", 6)],
    "base-cost": [_set("transaction_costs.scenarios.0.one_way_bps", 11.0)],
    "stress-cost": [_set("transaction_costs.scenarios.1.one_way_bps", 25.0)],
    "scenario-name": [_set("transaction_costs.scenarios.2.name", "zero")],
    "gross-exposure": [_set("portfolio.max_gross_exposure", 0.9)],
    "holdout-reason": [_set("final_holdout.reason", "A different documented reason.")],
    "universe-version-only": [_set("universe.version", "EXPERIMENTAL_TEST")],
    "universe-rule": [
        _set("universe.version", "EXPERIMENTAL_TEST"),
        _set("universe.max_constituents", 500),
    ],
}


@pytest.mark.parametrize("edits", SEMANTIC_EDITS.values(), ids=SEMANTIC_EDITS.keys())
def test_semantic_change_changes_hash(edits: list[Callable[[dict[str, Any]], None]]) -> None:
    data = _base_data()
    for edit in edits:
        edit(data)
    changed = _load(data)
    assert changed != load_phase1_config(BASE_YAML)
    assert config_hash(changed) != config_hash(load_phase1_config(BASE_YAML))


@given(h1=st.integers(min_value=1, max_value=10_000), h2=st.integers(min_value=1, max_value=10_000))
def test_hash_distinguishes_horizons(h1: int, h2: int) -> None:
    def with_horizon(h: int) -> str:
        data = _base_data()
        data["primary_target"]["horizon_sessions"] = h
        return config_hash(_load(data))

    assert (with_horizon(h1) == with_horizon(h2)) == (h1 == h2)


def test_yaml_and_json_round_trips_preserve_values() -> None:
    cfg = load_phase1_config(BASE_YAML)
    via_yaml = load_yaml_config(dump_yaml_config(cfg), Phase1Config)
    via_json = Phase1Config.model_validate_json(cfg.model_dump_json())
    assert via_yaml == cfg
    assert via_json == cfg
    assert config_hash(via_yaml) == config_hash(via_json) == config_hash(cfg)


def test_config_is_immutable() -> None:
    cfg = load_phase1_config(BASE_YAML)
    with pytest.raises(ValidationError):
        cfg.primary_target.horizon_sessions = 10  # type: ignore[misc]


@given(
    base_bps=st.floats(min_value=0.01, max_value=100, allow_nan=False),
    stress_extra=st.floats(min_value=0, max_value=100, allow_nan=False),
    horizon=st.integers(min_value=1, max_value=260),
    min_price=st.floats(min_value=0.01, max_value=1_000, allow_nan=False),
    max_constituents=st.integers(min_value=1, max_value=10_000),
)
def test_arbitrary_valid_configs_round_trip_through_yaml(
    base_bps: float, stress_extra: float, horizon: int, min_price: float, max_constituents: int
) -> None:
    data = _base_data()
    data["primary_target"]["horizon_sessions"] = horizon
    data["universe"].update(
        version="EXPERIMENTAL_TEST", min_price_usd=min_price, max_constituents=max_constituents
    )
    data["transaction_costs"]["scenarios"][0]["one_way_bps"] = base_bps
    data["transaction_costs"]["scenarios"][1]["one_way_bps"] = base_bps + stress_extra
    cfg = _load(data)
    restored = load_yaml_config(dump_yaml_config(cfg), Phase1Config)
    assert restored == cfg
    assert config_hash(restored) == config_hash(cfg)


# --- loader strictness -------------------------------------------------------------------


def test_duplicate_yaml_keys_rejected() -> None:
    text = BASE_YAML.read_text(encoding="utf-8") + "\nphase: phase1\n"
    with pytest.raises(ConfigSyntaxError, match="duplicate key 'phase'"):
        load_yaml_config(text, Phase1Config)


def test_non_string_yaml_keys_rejected() -> None:
    with pytest.raises(ConfigSyntaxError, match="non-string key"):
        load_yaml_config("1: x\n", Phase1Config)


def test_unknown_keys_rejected_at_every_level() -> None:
    top = {**_base_data(), "leverage": 2.0}
    nested = _base_data()
    nested["universe"]["include_otc"] = True
    for data in (top, nested):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            _load(data)


@pytest.mark.parametrize(
    "replacement",
    [
        "min_price_usd: '5.0'",
        "min_price_usd: .nan",
        "min_price_usd: .inf",
        "min_price_usd: true",
        "min_price_usd: null",
    ],
)
def test_ambiguous_or_non_finite_yaml_scalars_rejected(replacement: str) -> None:
    text = BASE_YAML.read_text(encoding="utf-8").replace("min_price_usd: 5.0", replacement)
    assert replacement in text
    with pytest.raises(ValidationError):
        load_yaml_config(text, Phase1Config)


# --- portfolio and holdout ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [("long_only", False), ("max_gross_exposure", 1.5), ("max_gross_exposure", 0.0)],
)
def test_short_or_levered_portfolio_rejected(field: str, value: object) -> None:
    data = _base_data()
    data["portfolio"][field] = value
    with pytest.raises(ValidationError):
        _load(data)


def test_unset_holdout_cannot_carry_dates() -> None:
    with pytest.raises(ValidationError, match="unset final holdout"):
        FinalHoldout(
            status="unset",
            reason="awaiting audit",
            interval=None,
            frozen_on=date(2026, 1, 1),
        )


def test_frozen_holdout_requires_dates() -> None:
    with pytest.raises(ValidationError, match="frozen final holdout requires"):
        load_yaml_config(
            "status: frozen\nreason: audit complete\ninterval: null\nfrozen_on: null\n",
            FinalHoldout,
        )


def test_holdout_reason_required() -> None:
    with pytest.raises(ValidationError):
        load_yaml_config(
            "status: unset\nreason: '  '\ninterval: null\nfrozen_on: null\n", FinalHoldout
        )
