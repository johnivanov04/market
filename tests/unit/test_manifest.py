"""Invariants of the experiment reproducibility manifest."""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from equity_research.config import (
    REQUIRED_PROVENANCE_FIELDS,
    ExperimentManifest,
    config_hash,
    load_phase1_config,
    load_yaml_config,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = load_phase1_config(REPO_ROOT / "configs" / "phase1" / "base.yaml")


def _load(data: object) -> ExperimentManifest:
    return load_yaml_config(json.dumps(data), ExperimentManifest)


def _valid() -> dict[str, Any]:
    return {
        "experiment_id": "exp-0001",
        "dataset_snapshot_id": "snapshot-2026-01-01",
        "source_identity": "example-vendor/example-table",
        "universe": BASE.universe.model_dump(mode="json"),
        "feature_version": "features-v0",
        "label_definition": BASE.primary_target.model_dump(mode="json"),
        "signal_execution_convention": BASE.timing.model_dump(mode="json"),
        "rebalance_rule": BASE.rebalance.model_dump(mode="json"),
        "strategy_version": "strategy-v0",
        "hyperparameters": {"lookback": 20, "shrink": 0.5, "flag": True, "note": None},
        "random_seed": None,
        "transaction_costs": BASE.transaction_costs.model_dump(mode="json"),
        "portfolio": BASE.portfolio.model_dump(mode="json"),
        "training_interval": {"start": "2010-01-01", "end": "2015-12-31"},
        "validation_interval": {"start": "2016-01-01", "end": "2017-12-31"},
        "test_interval": {"start": "2018-01-01", "end": "2019-12-31"},
        "is_final_holdout": False,
        "code_git_commit": "0123456789abcdef0123456789abcdef01234567",
        "config_hash": config_hash(BASE),
    }


def test_valid_manifest_round_trips() -> None:
    manifest = _load(_valid())
    assert _load(manifest.model_dump(mode="json")) == manifest
    assert ExperimentManifest.model_validate_json(manifest.model_dump_json()) == manifest


def test_required_fields_are_exactly_the_pinned_provenance_set() -> None:
    fields = ExperimentManifest.model_fields
    assert set(fields) == REQUIRED_PROVENANCE_FIELDS
    assert all(info.is_required() for info in fields.values())


@pytest.mark.parametrize("field", sorted(REQUIRED_PROVENANCE_FIELDS))
def test_omitting_any_provenance_field_is_rejected(field: str) -> None:
    data = _valid()
    del data[field]
    with pytest.raises(ValidationError) as excinfo:
        _load(data)
    assert any(e["type"] == "missing" and e["loc"] == (field,) for e in excinfo.value.errors())


def test_random_seed_must_be_explicit_but_may_be_null() -> None:
    assert _load({**_valid(), "random_seed": None}).random_seed is None
    assert _load({**_valid(), "random_seed": 7}).random_seed == 7


def test_unknown_field_rejected() -> None:
    with pytest.raises(ValidationError):
        _load({**_valid(), "notes_that_are_not_provenance": "x"})


@pytest.mark.parametrize(
    "commit",
    ["HEAD", "main", "0123456", "0123456789ABCDEF0123456789ABCDEF01234567", ""],
)
def test_code_commit_must_be_full_lowercase_sha(commit: str) -> None:
    with pytest.raises(ValidationError):
        _load({**_valid(), "code_git_commit": commit})


@pytest.mark.parametrize("digest", ["", "abc", "sha256:" + "0" * 64, "G" * 64])
def test_config_hash_must_be_sha256_hex(digest: str) -> None:
    with pytest.raises(ValidationError):
        _load({**_valid(), "config_hash": digest})


@pytest.mark.parametrize(
    ("validation", "test"),
    [
        (
            {"start": "2015-06-01", "end": "2017-12-31"},
            {"start": "2018-01-01", "end": "2019-12-31"},
        ),
        (
            {"start": "2016-01-01", "end": "2018-06-30"},
            {"start": "2018-01-01", "end": "2019-12-31"},
        ),
        (
            {"start": "2016-01-01", "end": "2017-12-31"},
            {"start": "2012-01-01", "end": "2013-12-31"},
        ),
    ],
)
def test_overlapping_or_misordered_intervals_rejected(
    validation: dict[str, str], test: dict[str, str]
) -> None:
    with pytest.raises(ValidationError, match="must start strictly after"):
        _load({**_valid(), "validation_interval": validation, "test_interval": test})


def test_interval_end_before_start_rejected() -> None:
    with pytest.raises(ValidationError, match="after end"):
        _load({**_valid(), "test_interval": {"start": "2019-12-31", "end": "2018-01-01"}})


@given(seed=st.one_of(st.none(), st.integers(min_value=0, max_value=2**63 - 1)))
def test_manifest_json_round_trip_preserves_values(seed: int | None) -> None:
    manifest = _load({**_valid(), "random_seed": seed})
    restored = ExperimentManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest
    assert config_hash(restored) == config_hash(manifest)


def test_experiment_contract_doc_lists_every_manifest_field() -> None:
    doc = (REPO_ROOT / "docs" / "experiment_contract.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"`([a-z_]+)`", doc))
    assert documented >= REQUIRED_PROVENANCE_FIELDS
