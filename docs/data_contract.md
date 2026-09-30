# Data contract

Status: **requirements only**. No data source is integrated, no credentials exist, and
no data has been downloaded. This document defines what normalized data must provide
before any research code may use it.

## Security identity

- **Stable internal security identifier** that never changes for the life of a
  security and is never reused. Tickers are *not* identifiers.
- **Effective-dated ticker history:** `(security_id, ticker, valid_from, valid_to)`.
- **Exchange / listing history:** effective-dated exchange, listing date, and
  delisting date with delisting reason where available.
- **Security type**, effective-dated where the source allows, sufficient to apply
  the exclusions in `universe_contract.md`.

## Prices and corporate actions

- **Raw / unadjusted OHLCV** per security per regular session. This is the primary
  price record.
- **Vendor-adjusted fields retained separately**, in clearly named columns or
  tables. They never overwrite raw fields.
- **Corporate actions:** splits, reverse splits, spin-offs, mergers and symbol changes,
  with ex/effective dates.
- **Dividends:** cash and special dividends, with declaration, ex, record and pay
  dates where available.
- **Delisting handling:** the final tradable price and the delisting return (or an
  explicit, documented assumption when the source lacks one). Delisted securities
  remain in history.
- **Benchmark data**, e.g. a broad U.S. market total-return series, stored with the
  same provenance requirements.

## Provenance

Every normalized record must trace back to:

- **Source identity:** vendor, product/table, and version or endpoint.
- **Raw immutable snapshot ID** identifying the exact raw extract it was derived from.
- **Content / hash metadata** where practical, e.g. a SHA-256 of each raw file, so
  a snapshot can be verified as unchanged.

Raw snapshots are **write-once**. Normalized data is **derived** and can be rebuilt
from raw snapshots plus code. **Raw and normalized data must never silently overwrite
one another.** A new vendor extract is a new snapshot, not an in-place update.

## Availability semantics

Every non-price fact, such as fundamentals, classifications, share counts or
corporate-action announcements, carries a **`known_at`** timestamp: the earliest time
it was available. It is distinct from the period or observation date it describes
(see `time_and_execution_contract.md`). Where a source provides no reliable
availability time, the loader must apply an explicit, documented conservative lag.
It must not assume the data was known at period end.

Restated values are new records with their own `known_at`. They never replace the
originally reported values in point-in-time queries.

## Sources

| Source | Status | Intended role |
|---|---|---|
| Sharadar SEP (prices) + SF1 (fundamentals) | **Leading candidate. Not yet approved.** | Primary source, subject to the data-coverage audit |
| Norgate Data | Potential | Independent validation of prices, corporate actions and delistings |
| CRSP | Potential | Independent validation, especially delisting returns and survivorship |

No vendor SDK, client, subscription or credential is part of this repository yet.
Approving a vendor is an explicit, recorded decision that follows the data-coverage
audit.
