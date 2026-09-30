"""Runtime deep immutability of validated configs and experiment manifests.

Invariant: once a validated config or manifest exists, neither a top-level field nor
any nested value can be changed through that instance. Read-only typing is not relied
on; every check here is a runtime check.
"""

import copy
import json
import pickle
from collections.abc import Callable, Iterable, Iterator
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError

from equity_research.config import (
    FROZEN_UNIVERSE_VERSIONS,
    INITIAL_UNIVERSE_V1,
    INITIAL_UNIVERSE_V1_ID,
    ExperimentManifest,
    FrozenMap,
    config_hash,
    load_phase1_config,
)

BASE = load_phase1_config(Path(__file__).resolve().parents[2] / "configs" / "phase1" / "base.yaml")

IMMUTABLE_LEAVES = (str, int, float, bool, type(None), date)

json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
)


def _manifest_data(hyperparameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_id": "exp-0001",
        "dataset_snapshot_id": "snapshot-1",
        "source_identity": "example-vendor/example-table",
        "universe": BASE.universe.model_dump(mode="json"),
        "feature_version": "features-v0",
        "label_definition": BASE.primary_target.model_dump(mode="json"),
        "signal_execution_convention": BASE.timing.model_dump(mode="json"),
        "rebalance_rule": BASE.rebalance.model_dump(mode="json"),
        "strategy_version": "strategy-v0",
        "hyperparameters": hyperparameters,
        "random_seed": 7,
        "transaction_costs": BASE.transaction_costs.model_dump(mode="json"),
        "portfolio": BASE.portfolio.model_dump(mode="json"),
        "training_interval": {"start": "2010-01-01", "end": "2015-12-31"},
        "validation_interval": {"start": "2016-01-01", "end": "2017-12-31"},
        "test_interval": {"start": "2018-01-01", "end": "2019-12-31"},
        "is_final_holdout": False,
        "code_git_commit": "0123456789abcdef0123456789abcdef01234567",
        "config_hash": config_hash(BASE),
    }


def _manifest(hyperparameters: dict[str, Any] | None = None) -> ExperimentManifest:
    hp = {"lookback": 20, "shrink": 0.5} if hyperparameters is None else hyperparameters
    return ExperimentManifest.model_validate_json(json.dumps(_manifest_data(hp)))


def _mutable_values(value: object, path: str) -> Iterator[str]:
    """Yield the path of every reachable value that is not of a known-immutable kind."""
    if isinstance(value, BaseModel):
        if not value.model_config.get("frozen"):
            yield f"{path} (non-frozen model {type(value).__name__})"
        for name in type(value).model_fields:
            yield from _mutable_values(getattr(value, name), f"{path}.{name}")
    elif isinstance(value, FrozenMap):
        for key, item in cast("FrozenMap[object, object]", value).items():
            yield from _mutable_values(item, f"{path}[{key!r}]")
    elif isinstance(value, tuple | frozenset):
        for i, item in enumerate(cast("Iterable[object]", value)):
            yield from _mutable_values(item, f"{path}[{i}]")
    elif not isinstance(value, IMMUTABLE_LEAVES):
        yield f"{path} ({type(value).__name__})"


@pytest.mark.parametrize(
    "instance",
    [BASE, _manifest(), _manifest({}), INITIAL_UNIVERSE_V1],
    ids=["phase1-config", "manifest", "manifest-empty-hyperparameters", "universe-v1"],
)
def test_every_reachable_value_is_immutable(instance: BaseModel) -> None:
    assert list(_mutable_values(instance, type(instance).__name__)) == []


def test_top_level_and_nested_field_assignment_rejected() -> None:
    manifest = _manifest()
    with pytest.raises(ValidationError, match="frozen"):
        manifest.hyperparameters = {"lookback": 99}  # type: ignore[misc]
    with pytest.raises(ValidationError, match="frozen"):
        manifest.portfolio.max_gross_exposure = 2.0  # type: ignore[misc]
    with pytest.raises(ValidationError, match="frozen"):
        manifest.transaction_costs.scenarios[0].one_way_bps = 0.0  # type: ignore[misc]
    with pytest.raises(ValidationError, match="frozen"):
        BASE.universe.min_price_usd = 1.0  # type: ignore[misc]
    with pytest.raises(ValidationError, match="frozen"):
        BASE.final_holdout.frozen_on = date(2026, 1, 1)  # type: ignore[misc]


def test_hyperparameters_cannot_be_mutated_in_place() -> None:
    manifest = _manifest()
    before = (manifest.model_dump_json(), config_hash(manifest))
    hp: Any = manifest.hyperparameters
    with pytest.raises(TypeError):
        hp["lookback"] = 99
    with pytest.raises(TypeError):
        del hp["lookback"]
    for method in ("update", "clear", "pop", "popitem", "setdefault"):
        assert not hasattr(hp, method)
    with pytest.raises(TypeError):
        hp._data["lookback"] = 99  # the private backing store is read-only too
    with pytest.raises(AttributeError, match="immutable"):
        hp._data = {"lookback": 99}
    assert (manifest.model_dump_json(), config_hash(manifest)) == before


def test_manifest_does_not_alias_caller_input() -> None:
    source = {"lookback": 20}
    data = _manifest_data(source)
    manifest = ExperimentManifest.model_validate(
        {**json.loads(json.dumps(data)), "hyperparameters": source},
        strict=False,
    )
    source["lookback"] = 99
    source["injected"] = 1
    assert dict(manifest.hyperparameters) == {"lookback": 20}


def test_nested_collections_are_tuples() -> None:
    classes: Any = BASE.universe.excluded_security_classes
    scenarios: Any = BASE.transaction_costs.scenarios
    with pytest.raises(AttributeError):
        classes.append("common_stock")
    with pytest.raises(TypeError):
        scenarios[0] = scenarios[1]


def test_frozen_universe_registry_cannot_be_altered() -> None:
    registry: Any = FROZEN_UNIVERSE_VERSIONS
    with pytest.raises(TypeError):
        registry["INITIAL_UNIVERSE_V2"] = {}
    with pytest.raises(TypeError):
        registry[INITIAL_UNIVERSE_V1_ID]["min_price_usd"] = 1.0
    with pytest.raises(TypeError):
        del registry[INITIAL_UNIVERSE_V1_ID]
    assert registry[INITIAL_UNIVERSE_V1_ID]["min_price_usd"] == 5.0


def _pickle_roundtrip(m: ExperimentManifest) -> ExperimentManifest:
    return pickle.loads(pickle.dumps(m))


def _model_copy_deep(m: ExperimentManifest) -> ExperimentManifest:
    return m.model_copy(deep=True)


@pytest.mark.parametrize(
    "roundtrip",
    [copy.deepcopy, _pickle_roundtrip, _model_copy_deep],
    ids=["deepcopy", "pickle", "model_copy-deep"],
)
def test_copies_preserve_values_and_immutability(
    roundtrip: Callable[[ExperimentManifest], ExperimentManifest],
) -> None:
    manifest = _manifest()
    clone = roundtrip(manifest)
    assert clone == manifest
    assert config_hash(clone) == config_hash(manifest)
    assert isinstance(clone.hyperparameters, FrozenMap)
    assert list(_mutable_values(clone, "clone")) == []


@given(hp=st.dictionaries(st.text(), json_scalars, max_size=8), data=st.data())
def test_hyperparameters_frozen_canonical_and_order_independent(
    hp: dict[str, Any], data: st.DataObject
) -> None:
    shuffled_keys = data.draw(st.permutations(list(hp)))
    shuffled = {k: hp[k] for k in shuffled_keys}
    a, b = _manifest(hp), _manifest(shuffled)
    assert isinstance(a.hyperparameters, FrozenMap)
    assert dict(a.hyperparameters) == hp
    assert list(a.hyperparameters) == sorted(hp)
    assert a.model_dump_json() == b.model_dump_json()
    assert config_hash(a) == config_hash(b)
    assert ExperimentManifest.model_validate_json(a.model_dump_json()) == a


def test_phase1_config_has_no_mutable_escape_hatch_via_dump() -> None:
    dumped = BASE.model_dump()
    dumped["universe"]["min_price_usd"] = 1.0
    dumped["transaction_costs"]["scenarios"][0]["one_way_bps"] = 0.0
    assert BASE.universe.min_price_usd == 5.0
    assert BASE.transaction_costs.scenarios[0].one_way_bps == 10.0
