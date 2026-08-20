# Crypto V4 Avalanche 365d Evidence Allocation Governance

## Status

**Governed exception approved for pre-scoring evidence allocation.**

This document governs the `avalanche` 365-day group inside `CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4` after the preflight and allocation audits identified a genuine chronology bottleneck before any V4 development scoring or V4 final-holdout outcome viewing.

## Evidence

The dedicated Avalanche365 bottleneck audit established:

- common development-safe origins: `59`;
- 50th common development-safe origin: `2025-06-26`;
- latest common development-safe origin: `2025-07-07`;
- holdout-safe origins: `964`;
- holdout-safe origins strictly after the 50th common development-safe origin: `9`;
- all three frozen 365d candidate families have the same 59 development-safe origins;
- V4 holdout outcome values, signs, and magnitudes were not read;
- source evidence was not modified.

Therefore the originally frozen `50 development + 10 final holdout` allocation cannot be satisfied for Avalanche365 while simultaneously preserving:

1. the full 50-origin development sample;
2. common development origins across all three candidate families;
3. a strictly later chronological final-holdout boundary; and
4. exact calendar-date target availability.

## Governed decision

For `avalanche` at 365 days only:

- development origins remain `50`;
- development folds remain `5` folds of `10` origins;
- final-holdout origins are reduced from `10` to `9`;
- all 9 final-holdout origins must be strictly later than the latest selected development origin;
- the 9 holdout origins must be the latest eligible holdout-safe dates after the selected development boundary;
- development origins must remain common across all three frozen Avalanche365 candidate families;
- exact calendar-date target availability remains mandatory;
- no V4 holdout outcome value, sign, or magnitude may be read before the development winner or `NO_QUALIFIED_WINNER` sentinel is frozen.

All other V4 groups remain at `50 development + 10 final holdout`.

## Rationale

Reducing the Avalanche365 final holdout by one observation is the smallest defensible exception. It preserves the full five-fold development comparison and avoids weakening candidate selection, altering candidate families, lowering promotion criteria, or violating the chronological final-test boundary.

A `49 development + 10 holdout` allocation would break the frozen five-fold structure. A `45 development + 10 holdout` allocation would preserve fold symmetry but unnecessarily discard five development observations. Allowing a holdout date to precede the final development date would contaminate the intended final-test chronology. The governed `50 + 9` exception changes only the minimum necessary dimension.

## Statistical interpretation

The Avalanche365 final confirmation sample will contain 9 observations rather than 10. This must be reported explicitly in final V4 results. No weighting, duplication, synthetic observation, or denominator normalization may be used to conceal the unequal group size.

The 365-day aggregate final-holdout sample will therefore contain 49 observations across the five supported assets if all other groups retain 10 observations.

## Scope boundary

This exception is an evidence-allocation correction discovered before V4 model scoring. It does not change:

- the V4 candidate families;
- the 365d primary target;
- the 365d trivial baseline;
- the 365d development promotion gate;
- transaction-cost assumptions;
- recommendation-policy semantics;
- the V3 final holdout;
- any V3 result.

## Required correction

The V4 holdout manifest must be rebuilt under the governed allocation rule and must record the Avalanche365 exception explicitly. The corrected manifest must be content-hashed and validated before V4 development scoring resumes.

## Next gate

`REBUILD_AND_VALIDATE_V4_MEMBERSHIP_WITH_AVALANCHE365_50_DEV_9_FINAL_EXCEPTION`
