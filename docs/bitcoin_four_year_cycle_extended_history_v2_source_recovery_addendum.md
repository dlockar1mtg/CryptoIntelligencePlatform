# Bitcoin Four-Year Cycle Extended History V2 — Source Recovery Addendum

## Status

This addendum governs recovery from the failed initial extended-history acquisition attempt for `BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2`.

## Failed source attempt

The initially frozen V2 source metric was Coin Metrics Community API `ReferenceRateUSD` at daily frequency.

The acquisition preflight passed, but execution failed because the returned `ReferenceRateUSD` history did not reach the required 2011 coverage boundary. No source snapshot was written, no canonical database change occurred, no cycle-policy authority was granted, and no production policy changed.

The failed attempt is evidence that `ReferenceRateUSD` is not suitable for the required early-cycle coverage. It must not be retried as if it satisfied the V2 history requirement.

## Governed recovery source

V2 retains Coin Metrics Community API as the provider but substitutes the daily Bitcoin asset metric:

`PriceUSD`

for the failed `ReferenceRateUSD` metric.

Coin Metrics catalog metadata documents daily BTC `PriceUSD` coverage beginning in 2010, which is sufficient to evaluate the first required completed halving interval beginning with the 2012 halving.

This is a research-source substitution only. It does not alter the canonical Crypto database and does not redefine the V1 study.

## Source semantics

The V2 recovery snapshot must be classified as:

`EXTERNAL_HISTORICAL_RESEARCH_SNAPSHOT_NOT_STRICT_VINTAGE_POINT_IN_TIME`

The snapshot is historical research evidence, not a strict vintage point-in-time market feed and not a production pricing authority.

## Required source boundaries

The recovery acquisition must:

- use Coin Metrics Community API;
- use asset `btc`;
- use metric `PriceUSD`;
- use frequency `1d`;
- request history beginning no later than 2011-01-01;
- request history through the current governed study end date;
- require observed source coverage on or before 2011-01-01;
- require exact daily observations surrounding the governed halving anchors;
- retain missing source dates as missing;
- prohibit interpolation, forward-fill, backward-fill, nearest-date substitution, and synthetic prices;
- normalize to one positive BTC USD price per UTC calendar date;
- write only a frozen research snapshot outside the canonical database.

## Required historical anchors

The acquisition must preserve exact source observations for at least:

- 2012-11-27;
- 2016-07-08;
- 2020-05-10;
- 2024-04-19.

These checks establish coverage around the governed halving anchors without substituting a nearby observation.

## Unchanged analytical design

This source recovery does not change the V2 analytical question, phase definitions, holding horizons, cycle intervals, or certification criteria.

The intended completed intervals remain:

- `2012-11-28 -> 2016-07-09`;
- `2016-07-09 -> 2020-05-11`;
- `2020-05-11 -> 2024-04-20`.

The primary strategic accumulation diagnostic remains exact three-year forward outcomes, with the refined expansion-peak/reset-trough diagnostic defined in the V2 design.

## Prohibited effects

This recovery does not authorize:

- modification of `data/crypto_intelligence.duckdb`;
- use of the external snapshot as canonical production price authority;
- model fitting or recommendation-threshold optimization;
- reinterpretation of frozen V4 model results;
- cycle-policy certification before V2 study review;
- autonomous execution;
- production-policy changes.

## Authority

`CYCLE_POLICY_AUTHORITY_GRANTED=FALSE`

`CANONICAL_DATABASE_WRITE_ALLOWED=FALSE`

`PRODUCTION_POLICY_CHANGE_ALLOWED=FALSE`

## Next gate

`RETRY_EXTENDED_HISTORY_SOURCE_ACQUISITION_WITH_PRICEUSD`
