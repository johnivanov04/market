"""Reproducibility manifest required for every experiment. See ``docs/experiment_contract.md``.

A backtest result without a complete reproducibility manifest is not a valid research
result. Every field below is required and has no default; ``random_seed`` must be given
explicitly even when it is ``None`` (not applicable).
"""

from typing import Annotated, Self

from pydantic import StringConstraints, model_validator

from equity_research.config._base import (
    DateInterval,
    FrozenModel,
    FrozenScalarMap,
    Identifier,
    NonEmptyText,
)
from equity_research.config.costs import TransactionCostModel
from equity_research.config.phase1 import PortfolioPolicy
from equity_research.config.timing import PrimaryTargetSpec, RebalanceRule, TimingConvention
from equity_research.config.universe import UniverseSpec

GitCommit = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
"""Full 40-character lowercase SHA-1 commit; abbreviated or symbolic refs are not accepted."""

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ExperimentManifest(FrozenModel):
    experiment_id: Identifier
    dataset_snapshot_id: Identifier
    source_identity: NonEmptyText
    universe: UniverseSpec
    feature_version: Identifier
    label_definition: PrimaryTargetSpec
    signal_execution_convention: TimingConvention
    rebalance_rule: RebalanceRule
    strategy_version: Identifier
    hyperparameters: FrozenScalarMap
    random_seed: int | None
    transaction_costs: TransactionCostModel
    portfolio: PortfolioPolicy
    training_interval: DateInterval
    validation_interval: DateInterval
    test_interval: DateInterval
    is_final_holdout: bool
    code_git_commit: GitCommit
    config_hash: Sha256Hex

    @model_validator(mode="after")
    def _intervals_ordered(self) -> Self:
        if not self.training_interval.end < self.validation_interval.start:
            raise ValueError("validation interval must start strictly after training ends")
        if not self.validation_interval.end < self.test_interval.start:
            raise ValueError("test interval must start strictly after validation ends")
        return self


REQUIRED_PROVENANCE_FIELDS: frozenset[str] = frozenset(
    {
        "experiment_id",
        "dataset_snapshot_id",
        "source_identity",
        "universe",
        "feature_version",
        "label_definition",
        "signal_execution_convention",
        "rebalance_rule",
        "strategy_version",
        "hyperparameters",
        "random_seed",
        "transaction_costs",
        "portfolio",
        "training_interval",
        "validation_interval",
        "test_interval",
        "is_final_holdout",
        "code_git_commit",
        "config_hash",
    }
)
"""Pinned list of manifest fields. Tests assert the model's required fields equal this set,
so removing a field or giving it a default is a deliberate, reviewed change."""
