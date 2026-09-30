# equity-research

An empirical research project that tests whether a systematic, long-only, weekly
U.S. equity strategy has a robust edge after costs. It is built so that results can
be trusted, and a negative result is an acceptable outcome.

## Phase 1: research correctness, not ML

Phase 1 builds the foundations every later result depends on: point-in-time data,
a survivorship-free universe, correct signal/execution timing, cost-aware evaluation,
and reproducible experiment manifests. Phase 1 involves no machine learning and no
broker integration.

Phase progression (high level):

1. **Phase 1:** contracts, data audit and normalization, universe, labels, simple
   baselines, and an evaluation harness. The current step, 1A, covers only the
   repository foundation and the typed research contracts.
2. **Phase 2:** model development and tuning. This starts only after the final
   holdout is frozen.
3. **Later:** single evaluation on the final holdout, then any consideration of live
   operation.

## Research contracts

Frozen decisions live in [`docs/`](docs/). Their machine-readable form is
[`configs/phase1/base.yaml`](configs/phase1/base.yaml), validated by
`equity_research.config`:

- [Research contract](docs/research_contract.md)
- [Universe contract (`INITIAL_UNIVERSE_V1`)](docs/universe_contract.md)
- [Time and execution contract](docs/time_and_execution_contract.md)
- [Data contract](docs/data_contract.md)
- [Experiment contract](docs/experiment_contract.md)

## Setup

Requires [uv](https://docs.astral.sh/uv/). Python 3.12 is pinned in `.python-version`,
and uv installs it if needed.

```sh
uv sync
```

## Validation

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
git diff --check
```

Set `HYPOTHESIS_PROFILE=ci` to make property-based tests derandomized.

## Credentials

Do not add data-vendor or broker credentials, API keys, or tokens to this repository.
No data source or broker is integrated yet.
