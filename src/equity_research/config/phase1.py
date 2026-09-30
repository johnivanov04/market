"""Root Phase-1 research configuration. Canonical instance: ``configs/phase1/base.yaml``."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from equity_research.config._base import DateInterval, FrozenModel, NonEmptyText
from equity_research.config.costs import TransactionCostModel
from equity_research.config.timing import PrimaryTargetSpec, RebalanceRule, TimingConvention
from equity_research.config.universe import UniverseSpec


class PortfolioPolicy(FrozenModel):
    long_only: Literal[True]
    max_gross_exposure: Annotated[float, Field(gt=0, le=1.0)]
    """Fraction of equity; values above 1.0 would be leverage and are not representable."""


class FinalHoldout(FrozenModel):
    """Final holdout period.

    Must remain ``unset`` until the data-coverage audit is complete, and must be
    ``frozen`` before any Phase-2 model tuning. Dates are never inferred.
    """

    status: Literal["unset", "frozen"]
    reason: NonEmptyText
    interval: DateInterval | None
    frozen_on: date | None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.status == "unset" and (self.interval is not None or self.frozen_on is not None):
            raise ValueError("an unset final holdout must not carry an interval or frozen_on date")
        if self.status == "frozen" and (self.interval is None or self.frozen_on is None):
            raise ValueError("a frozen final holdout requires both interval and frozen_on")
        return self


class Phase1Config(FrozenModel):
    schema_version: Literal[1]
    phase: Literal["phase1"]
    timing: TimingConvention
    rebalance: RebalanceRule
    primary_target: PrimaryTargetSpec
    portfolio: PortfolioPolicy
    universe: UniverseSpec
    transaction_costs: TransactionCostModel
    final_holdout: FinalHoldout
