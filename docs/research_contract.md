# Research contract

Status: **frozen for Phase 1**. Changing any decision below requires an explicit,
dated amendment to this document, a matching change to `configs/phase1/base.yaml`,
and updated tests. It must not happen as a side effect of implementation work.

Machine-readable form: `configs/phase1/base.yaml`, validated by
`equity_research.config.Phase1Config`.

## Scope

| Decision | Value |
|---|---|
| Market | U.S. equities |
| Direction | Long-only |
| Leverage | None (gross exposure <= 100% of equity) |
| Rebalance | Weekly |
| Signal time | After the regular-market close of the final U.S. regular trading session of each week |
| Earliest execution | Open of the next regular trading session |
| Same-close execution | Prohibited |
| Primary horizon | 5 regular trading sessions |

## Primary target

The cross-sectional rank (percentile) of each security's future **total return**,
measured from the **executable next open** (the execution session's open) to the
**open 5 regular trading sessions later**.

- "Total return" includes dividends and is adjusted for corporate actions in a way
  that uses only events whose effect is known by the relevant time (see
  `time_and_execution_contract.md`).
- The rank is taken across the eligible universe at that signal timestamp.

### Fixed 5-session horizon, not "until the next rebalance"

The primary label always covers a **fixed 5-regular-trading-session forward
horizon**: from the execution session's open to the open of the 5th regular session
after it. It is **not** redefined as "until the next calendar-week rebalance", and it is
never shortened or lengthened to line up with the rebalance schedule.

The weekly rebalance interval and the 5-session label window are therefore two
different quantities. They usually coincide, but around exchange holidays they can
differ, so consecutive weekly labels can overlap or, rarely, leave a gap. Later
validation and purging must use each observation's actual information (signal)
timestamp and label-end timestamp. They must not assume that weekly observations
have identical, non-overlapping calendar boundaries. Details and a worked example are
in `time_and_execution_contract.md`.

### Market adjustment is not embedded in the target

Subtracting the same market return from every stock does not change a
cross-sectional ranking: if `r_i > r_j` then `r_i - m > r_j - m`. A market-excess
target therefore adds nothing to the primary target. Beta-residual or
sector-relative adjustments *do* change rankings, because the amount subtracted
differs by stock. That is a separate hypothesis about what is predictable, so it
must be tested as a separate experiment and must not be folded silently into the
primary target.

### Secondary targets (not part of the initial implementation)

- 10-session and 20-session horizons
- Beta-residual return
- Sector-relative return

These are deferred experiments. The Phase-1 configuration schema cannot represent
them.

## Process constraints

- **No machine learning during Phase 1.** Phase 1 establishes data, universe,
  timing and evaluation correctness.
- **No broker integration during Phase 1.**
- **No live credentials in the repository**, at any phase. That covers data-vendor
  keys, broker keys, and tokens.
- **No final holdout dates have been selected.** They must be frozen *after* the
  data-coverage audit and *before* any Phase-2 model tuning. Until then the
  configuration records the holdout as `unset` with a reason, and no code may infer
  or default holdout dates.
- **Failure is an acceptable outcome.** If the eventual strategy shows no robust
  net-of-cost edge, that is a valid research result and is reported as such. Neither
  the contract nor the evaluation may be changed to rescue a result.
