"""Transaction-cost scenarios, expressed in basis points of one-way traded notional."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from equity_research.config._base import FrozenModel, Identifier

CostRole = Literal["base", "stress", "diagnostic"]
"""``base``: the cost assumption results are reported under.
``stress``: a harsher assumption every result must also be shown under.
``diagnostic``: never a reportable result (e.g. zero cost, used to isolate gross signal).
"""

BasisPoints = Annotated[float, Field(ge=0, le=10_000)]


class CostScenario(FrozenModel):
    name: Identifier
    role: CostRole
    one_way_bps: BasisPoints


class TransactionCostModel(FrozenModel):
    basis: Literal["one_way_traded_notional"]
    scenarios: tuple[CostScenario, ...]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        names = [s.name for s in self.scenarios]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate cost scenario names: {names}")

        base = [s for s in self.scenarios if s.role == "base"]
        stress = [s for s in self.scenarios if s.role == "stress"]
        if len(base) != 1:
            raise ValueError(f"exactly one base cost scenario required, found {len(base)}")
        if not stress:
            raise ValueError("at least one stress cost scenario required")
        for s in self.scenarios:
            if s.one_way_bps == 0 and s.role != "diagnostic":
                raise ValueError(f"zero-cost scenario {s.name!r} must have role 'diagnostic'")
        for s in stress:
            if s.one_way_bps < base[0].one_way_bps:
                raise ValueError(
                    f"stress scenario {s.name!r} ({s.one_way_bps} bps) is cheaper than "
                    f"base ({base[0].one_way_bps} bps)"
                )
        return self
