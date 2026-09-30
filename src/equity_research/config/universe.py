"""Candidate-universe specification. See ``docs/universe_contract.md``.

This module describes eligibility rules only; it does not construct a universe.
"""

from collections.abc import Mapping
from typing import Any, Literal, Self

from pydantic import field_validator, model_validator

from equity_research.config._base import (
    FrozenMap,
    FrozenModel,
    Identifier,
    PositiveCount,
    PositiveSessions,
    PositiveUsd,
)

ExcludedSecurityClass = Literal[
    "adr",
    "closed_end_fund",
    "etf_etp",
    "otc_only",
    "preferred",
    "right",
    "spac",
    "unit",
    "warrant",
]

INITIAL_UNIVERSE_V1_ID = "INITIAL_UNIVERSE_V1"

# Parameters of each frozen universe version. A spec that claims one of these version
# identifiers must match it exactly; changing a rule requires a new version identifier.
# Read-only at runtime so a definition cannot be altered after import.
FROZEN_UNIVERSE_VERSIONS: Mapping[str, Mapping[str, Any]] = FrozenMap(
    {
        INITIAL_UNIVERSE_V1_ID: FrozenMap(
            {
                "listing_scope": "us_major_exchange",
                "security_type": "common_operating_company_equity",
                "excluded_security_classes": (
                    "adr",
                    "closed_end_fund",
                    "etf_etp",
                    "otc_only",
                    "preferred",
                    "right",
                    "spac",
                    "unit",
                    "warrant",
                ),
                "eligibility_information": "point_in_time",
                "price_reference": "previous_known_price",
                "min_price_usd": 5.0,
                "liquidity_lookback_sessions": 60,
                "min_median_dollar_volume_usd": 20_000_000.0,
                "min_history_sessions": 252,
                "ranking_metric": "lagged_median_dollar_volume",
                "max_constituents": 1000,
            }
        ),
    }
)


class UniverseSpec(FrozenModel):
    version: Identifier
    listing_scope: Literal["us_major_exchange"]
    security_type: Literal["common_operating_company_equity"]
    excluded_security_classes: tuple[ExcludedSecurityClass, ...]
    eligibility_information: Literal["point_in_time"]
    price_reference: Literal["previous_known_price"]
    min_price_usd: PositiveUsd
    liquidity_lookback_sessions: PositiveSessions
    min_median_dollar_volume_usd: PositiveUsd
    min_history_sessions: PositiveSessions
    ranking_metric: Literal["lagged_median_dollar_volume"]
    max_constituents: PositiveCount

    @field_validator("excluded_security_classes")
    @classmethod
    def _unique_and_canonically_ordered(
        cls, value: tuple[ExcludedSecurityClass, ...]
    ) -> tuple[ExcludedSecurityClass, ...]:
        if len(set(value)) != len(value):
            raise ValueError("excluded_security_classes contains duplicates")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.min_history_sessions < self.liquidity_lookback_sessions:
            raise ValueError(
                "min_history_sessions must be >= liquidity_lookback_sessions so the "
                "liquidity filter is computable from prior history"
            )
        frozen = FROZEN_UNIVERSE_VERSIONS.get(self.version)
        if frozen is not None:
            actual = self.model_dump(exclude={"version"})
            diffs = sorted(
                k for k in frozen.keys() | actual.keys() if frozen.get(k) != actual.get(k)
            )
            if diffs:
                raise ValueError(
                    f"{self.version} is a frozen universe version; fields {diffs} differ from "
                    "its definition. Define a new version instead of redefining this one."
                )
        return self


INITIAL_UNIVERSE_V1 = UniverseSpec.model_validate(
    {"version": INITIAL_UNIVERSE_V1_ID, **FROZEN_UNIVERSE_VERSIONS[INITIAL_UNIVERSE_V1_ID]}
)
