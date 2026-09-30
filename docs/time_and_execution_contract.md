# Time and execution contract

Status: **frozen for Phase 1**. No exchange calendar is implemented yet. This
document defines semantics that a future calendar must satisfy.

## Canonical timezone

All market timestamps are interpreted in **`America/New_York`**. Timestamps are
stored timezone-aware. A naive timestamp is an error, not an assumption.

## Sessions

A **regular trading session** is a day on which the primary U.S. equity exchanges
hold their regular session. That is normally 09:30–16:00 ET, with early closes on
some days. Counts of "sessions" (horizon, lookbacks, history) always mean regular
trading sessions, never calendar days or weekdays.

## Four distinct times

Each piece of information has several times attached to it. They must never be
conflated:

| Time | Meaning |
|---|---|
| **Observation time** | The time the underlying fact refers to, e.g. the session a close price belongs to, or the fiscal period end of a financial statement. |
| **Information-availability time** (`known_at`) | The earliest time the fact was actually available to a market participant, e.g. a filing's publication timestamp. It is always >= observation time. |
| **Signal time** | The time at which a signal is formed. Only information with `known_at <= signal time` may be used. |
| **Execution time** | The earliest time a trade based on that signal may be filled. It is always strictly after signal time. |

## Signal timestamp

The signal is formed **after the regular-market close of the final regular trading
session of each week**. At that point that session's official close and all earlier
data are available. The signal uses information with `known_at` at or before that
moment.

## Execution timestamp

The earliest permitted execution is the **open of the next regular trading
session** after the signal session. That is usually the following Monday, or later if
Monday is a holiday.

## Prohibited: same-bar / same-close fills

A signal that uses a session's close must not be filled at that same close, or at
any price from that session. Doing so assumes a trade executed at a price that was
needed to decide the trade. The configuration schema has no representation for
same-close execution.

## Holiday-shortened weeks (conceptual)

- The **signal session** is the last regular session of the calendar week (Mon–Sun),
  whatever weekday it falls on. If Friday is a holiday, it is Thursday.
- The **execution session** is the next regular session, whatever weekday it falls on.
- Early-close sessions are regular sessions. Their close is the early close.
- A week with no regular session produces no signal.

## Fixed label horizon vs. weekly rebalance interval

The primary label is always a **fixed 5-regular-trading-session forward horizon**:

- label start = open of the execution session `E`;
- label end = open of regular session `E + 5`.

It is **not** redefined as "until the next calendar-week rebalance". The horizon
counts regular sessions only, and a holiday never shortens or lengthens it.

The **rebalance interval**, meaning the number of regular sessions from one weekly
execution open to the next, follows the calendar week. It is usually also 5 sessions,
but around exchange holidays the two can differ:

- **Overlap (common).** Suppose the signal is formed after Friday's close, Monday is a
  holiday, and execution is Tuesday's open (`E`). The label ends at the open of
  `E + 5`, the following Tuesday. The next rebalance executes at the following
  Monday's open (`E + 4`). The label window therefore extends one session past the
  next rebalance, so consecutive labels overlap. A mid-week holiday, e.g. Thanksgiving,
  has the same effect on the label that starts at that week's execution.
- **Gap (rare).** If more than 5 regular sessions separate two consecutive executions,
  e.g. because a week produces no signal after an unscheduled closure, the label ends
  before the next execution.

Consequences for later work (not implemented yet):

- Every observation must carry its own **information timestamp** (signal time) and
  **label-end timestamp** (the open of session `E + 5`).
- Train/validation/test splitting, purging and embargo must be computed from those
  per-observation timestamps. They must not assume that weekly observations have
  identical, non-overlapping calendar boundaries, or exactly 5 sessions between
  rebalances.

## Corporate-action adjustments and look-ahead

Vendor-adjusted price histories are typically **back-adjusted**: when a split or
dividend occurs, all *earlier* prices are rescaled. A back-adjusted price for a past
date is therefore a number that **did not exist** at that date. It encodes knowledge
of corporate actions that happened later.

Consequences:

- Price-level filters (e.g. `price >= $5`) and dollar-volume filters must use
  **raw, unadjusted** prices and volumes as known at the time.
- Returns across a corporate action must be computed from raw prices plus the
  corporate-action and dividend records whose effective date is inside the return
  window. Back-adjusted series must not stand in for them without verification.
- Adjusted fields may be retained for validation and convenience. They must never be
  treated as the contemporaneously known price.
