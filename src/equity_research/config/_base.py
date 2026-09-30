"""Shared base model and constrained scalar types for research configuration.

Design rule used throughout ``equity_research.config``:

* Categorical conventions whose alternatives the research contract *prohibits*
  (e.g. same-close execution, short positions) are ``Literal`` types, so an
  alternative cannot even be represented without a code change.
* Numeric parameters are range-validated. Their specific Phase-1 values are
  pinned by versioned definitions (see ``universe.FROZEN_UNIVERSE_VERSIONS``) and by
  tests against ``configs/phase1/base.yaml``.

All models are deeply immutable, reject unknown keys, and validate in strict mode: a
YAML ``"5"`` or ``true`` is not silently coerced into a number. Deep immutability means
every field value is a frozen model, an immutable scalar, a ``tuple``, or a ``FrozenMap``;
``tests/unit/test_immutability.py`` enforces this for every reachable value.
"""

from collections.abc import Iterator, Mapping
from datetime import date
from types import MappingProxyType
from typing import Annotated, Any, NoReturn, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    model_validator,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
        validate_default=True,
    )


Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:\-]*$")]
"""Machine-readable identifier: no whitespace, no leading punctuation."""

NonEmptyText = Annotated[str, StringConstraints(pattern=r"\S")]
"""Free text containing at least one non-whitespace character."""

PositiveSessions = Annotated[int, Field(gt=0)]
"""A count of regular U.S. trading sessions (not calendar days)."""

PositiveUsd = Annotated[float, Field(gt=0)]

PositiveCount = Annotated[int, Field(gt=0)]


class FrozenMap[K, V](Mapping[K, V]):
    """Read-only mapping that owns a private copy of its contents.

    Unlike a bare ``types.MappingProxyType`` it survives ``copy.deepcopy`` and pickling
    (and therefore ``model_copy(deep=True)``), which reconstruct it from a plain dict.
    """

    __slots__ = ("_data",)
    _data: Mapping[K, V]

    def __init__(self, data: Mapping[K, V]) -> None:
        object.__setattr__(self, "_data", MappingProxyType(dict(data)))

    def __getitem__(self, key: K) -> V:
        return self._data[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"FrozenMap({dict(self._data)!r})"

    def __reduce__(self) -> tuple[type[Self], tuple[dict[K, V]]]:
        return (type(self), (dict(self._data),))

    def __setattr__(self, name: str, value: Any) -> NoReturn:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError(f"{type(self).__name__} is immutable")


JsonScalar = str | int | float | bool | None


def _freeze_sorted(value: Mapping[str, JsonScalar]) -> FrozenMap[str, JsonScalar]:
    return FrozenMap(dict(sorted(value.items())))


def _thaw(value: Mapping[str, JsonScalar]) -> dict[str, JsonScalar]:
    return dict(value)


FrozenScalarMap = Annotated[
    Mapping[str, JsonScalar],
    AfterValidator(_freeze_sorted),
    PlainSerializer(_thaw),
]
"""Validated as a ``str -> JSON scalar`` mapping, stored as a key-sorted ``FrozenMap``
(so serialization order is canonical), serialized as a plain dict."""


class DateInterval(FrozenModel):
    """Closed interval of calendar dates, ``start <= end``."""

    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start > self.end:
            raise ValueError(f"interval start {self.start} is after end {self.end}")
        return self
