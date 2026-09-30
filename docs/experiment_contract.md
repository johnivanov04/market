# Experiment contract

**A backtest result without a complete reproducibility manifest is not a valid
research result.**

Every experiment must produce an `equity_research.config.ExperimentManifest`. Every
field is required and has no default. A test pins the field set
(`REQUIRED_PROVENANCE_FIELDS`), so removing a field or giving it a default is a
visible, reviewed change.

## Required manifest fields

| Requirement | Field | Notes |
|---|---|---|
| Experiment ID | `experiment_id` | Unique, machine-readable |
| Dataset snapshot / version | `dataset_snapshot_id` | Raw snapshot(s) the run was derived from |
| Source identity | `source_identity` | Vendor / product / table |
| Universe version | `universe` | Full `UniverseSpec`, including `version` |
| Feature version | `feature_version` | |
| Label definition | `label_definition` | Full `PrimaryTargetSpec` |
| Signal / execution convention | `signal_execution_convention` | Full `TimingConvention` |
| Rebalance rule | `rebalance_rule` | Full `RebalanceRule` |
| Model / strategy version | `strategy_version` | |
| Hyperparameters | `hyperparameters` | Flat mapping of JSON scalars. Empty is allowed but must be explicit |
| Random seed | `random_seed` | Integer, or explicit `null` when not applicable |
| Transaction-cost model | `transaction_costs` | All scenarios. Base and stress are both reported |
| Portfolio parameters | `portfolio` | |
| Training interval | `training_interval` | Closed date interval |
| Validation interval | `validation_interval` | Must start strictly after training ends |
| Test interval | `test_interval` | Must start strictly after validation ends |
| Final-holdout flag | `is_final_holdout` | `true` only for the single evaluation on the frozen holdout |
| Code Git commit | `code_git_commit` | Full 40-character SHA of a clean working tree |
| Config hash | `config_hash` | SHA-256 of canonical JSON (`equity_research.config.config_hash`) |

## Rules

- Results are reported under the **base** cost scenario and must also be shown under
  the **stress** scenario. Zero-cost results are **diagnostic only** and are never
  reported as performance.
- The final holdout is evaluated **once**, after the strategy is fixed. Any
  experiment that touches holdout dates before that point invalidates the holdout.
- A manifest describes the run that produced a result. It is written together with
  the result and never edited afterwards.
