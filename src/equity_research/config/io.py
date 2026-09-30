"""Deterministic YAML loading, serialization and hashing of configuration models.

YAML is parsed into plain data and then validated through Pydantic's strict JSON mode.
That combination rejects quoted numbers, booleans used as numbers, NaN/inf, unknown keys
and duplicate mapping keys instead of coercing or silently keeping the last value.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from equity_research.config.phase1 import Phase1Config


class ConfigSyntaxError(ValueError):
    pass


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate and non-string keys and keeps timestamps as strings."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)  # pyright: ignore[reportUnknownMemberType]
            if not isinstance(key, str):
                raise ConfigSyntaxError(f"non-string key {key!r} {key_node.start_mark}")
            if key in seen:
                raise ConfigSyntaxError(f"duplicate key {key!r} {key_node.start_mark}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _timestamp_as_string(loader: yaml.SafeLoader, node: yaml.Node) -> str:
    return str(loader.construct_scalar(node))  # pyright: ignore[reportArgumentType]


_StrictSafeLoader.add_constructor("tag:yaml.org,2002:timestamp", _timestamp_as_string)


def load_yaml_config[M: BaseModel](text: str, model: type[M]) -> M:
    data = yaml.load(text, Loader=_StrictSafeLoader)  # a SafeLoader subclass
    return model.model_validate_json(json.dumps(data))


def load_phase1_config(path: Path) -> Phase1Config:
    return load_yaml_config(path.read_text(encoding="utf-8"), Phase1Config)


def dump_yaml_config(config: BaseModel) -> str:
    return yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False, allow_unicode=False)


def canonical_json(config: BaseModel) -> str:
    return json.dumps(
        config.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def config_hash(config: BaseModel) -> str:
    """SHA-256 of the canonical JSON form. Independent of YAML formatting and key order."""
    return hashlib.sha256(canonical_json(config).encode("ascii")).hexdigest()
