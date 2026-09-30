# Universe contract: `INITIAL_UNIVERSE_V1`

Status: **frozen**. `INITIAL_UNIVERSE_V1` may not be redefined. Any change to a rule
below requires a new version identifier (for example `UNIVERSE_V2`), recorded here
with its date and rationale. The code enforces this: a `UniverseSpec` that claims
`INITIAL_UNIVERSE_V1` but differs from its frozen parameters fails validation
(`equity_research.config.universe.FROZEN_UNIVERSE_VERSIONS`).

Not yet implemented. This document specifies eligibility rules only.

## Point-in-time principle

At every historical signal timestamp, eligibility is decided using **only information
available by that timestamp**. Current index membership, current listing status,
current security type, current ticker, or any later reclassification must **never**
be used to decide historical eligibility. Securities that later delisted, merged or
went bankrupt must be present in the historical universe while they were eligible.

## Candidate security

A security is a candidate at a signal timestamp if, as known at that timestamp:

1. **Listing:** it is listed on a major U.S. exchange (`listing_scope: us_major_exchange`).
2. **Type:** it is common equity of an operating company.
3. **Exclusions (initially):**
   - ETFs / ETPs
   - closed-end funds
   - preferred shares
   - warrants
   - rights
   - units
   - SPACs
   - OTC-only securities
   - ADRs
4. **Price:** previous known price >= **$5.00**. This is the most recent price
   available at the signal timestamp, raw and unadjusted for later corporate actions.
5. **Liquidity:** median daily dollar volume over the prior **60** regular sessions
   >= **$20,000,000**.
6. **History:** at least **252** prior regular trading sessions of history.

## Size cap

Among candidates, retain at most the **1,000** securities with the highest lagged
60-session median dollar volume.

## Open questions for the data-coverage audit

These points do not change the rules above. They must be resolved, and recorded as
a new version if necessary, before the universe is implemented:

- The exact venue list behind "major U.S. exchange", for example whether Cboe-listed
  common stocks are included.
- Tie-breaking at the 1,000 boundary. It must be deterministic and must not use
  future information.
- How the vendor's security-type classification maps onto the exclusion list, and
  whether that classification is itself point-in-time.
- The treatment of trading halts and sessions with missing volume in the 60-session
  median.
- Whether "history" counts sessions under the stable security identifier across
  ticker changes. The intended answer is yes.
