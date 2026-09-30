"""Typed, immutable representation of the frozen Phase-1 research decisions."""

from equity_research.config._base import DateInterval, FrozenMap
from equity_research.config.costs import CostScenario, TransactionCostModel
from equity_research.config.io import (
    ConfigSyntaxError,
    canonical_json,
    config_hash,
    dump_yaml_config,
    load_phase1_config,
    load_yaml_config,
)
from equity_research.config.manifest import REQUIRED_PROVENANCE_FIELDS, ExperimentManifest
from equity_research.config.phase1 import FinalHoldout, Phase1Config, PortfolioPolicy
from equity_research.config.timing import (
    MARKET_TIMEZONE,
    PrimaryTargetSpec,
    RebalanceRule,
    TimingConvention,
)
from equity_research.config.universe import (
    FROZEN_UNIVERSE_VERSIONS,
    INITIAL_UNIVERSE_V1,
    INITIAL_UNIVERSE_V1_ID,
    UniverseSpec,
)

__all__ = [
    "FROZEN_UNIVERSE_VERSIONS",
    "INITIAL_UNIVERSE_V1",
    "INITIAL_UNIVERSE_V1_ID",
    "MARKET_TIMEZONE",
    "REQUIRED_PROVENANCE_FIELDS",
    "ConfigSyntaxError",
    "CostScenario",
    "DateInterval",
    "ExperimentManifest",
    "FinalHoldout",
    "FrozenMap",
    "Phase1Config",
    "PortfolioPolicy",
    "PrimaryTargetSpec",
    "RebalanceRule",
    "TimingConvention",
    "TransactionCostModel",
    "UniverseSpec",
    "canonical_json",
    "config_hash",
    "dump_yaml_config",
    "load_phase1_config",
    "load_yaml_config",
]
