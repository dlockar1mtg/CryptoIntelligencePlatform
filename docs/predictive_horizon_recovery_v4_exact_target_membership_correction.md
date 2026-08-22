# Crypto Native Predictive Horizon Recovery V4 — Exact-Target Membership Correction

## Status

**PRE-DEVELOPMENT EVIDENCE CORRECTION AUTHORIZED**

This correction is required because the first V4 development preflight identified one development origin whose exact calendar target endpoint was unavailable:

- asset: `xrp`
- horizon: `7d`
- origin: `2021-01-13`
- required exact target date: `2021-01-20`

The exhaustive availability audit checked all 850 V4 development origins and all 170 V4 final-holdout origins and found:

- development exact-target gaps: `1`
- final-holdout exact-target gaps: `0`
- holdout outcome values read: `false`
- source database modified: `false`

## Why the correction is valid

The original V4 membership freeze inherited the V3 feature-safe origin logic. V4 subsequently strengthened target semantics to require an exact `origin_date + horizon_days` calendar endpoint. The original membership freeze therefore did not fully encode the stricter V4 target rule.

No V4 model has been fitted or development-scored. No V4 final-holdout outcome has been read, summarized, or scored. The correction is therefore an evidence-boundary repair before model selection, not post-hoc tuning.

## Corrected rule

For every V4 asset × horizon group, candidate membership must satisfy all previously governed exclusions and feature-safety controls **plus** exact calendar target-date availability.

Membership selection must use date presence only. It must not read the future target price or derive any holdout outcome while selecting membership.

The deterministic allocation remains:

1. construct the fresh, feature-safe, exact-target-date-safe origin pool;
2. reserve the latest 10 eligible origins as the V4 final holdout;
3. select exactly 50 V4 development origins by deterministic chronological spacing from the remaining eligible pool;
4. preserve all V2, V3 development, V3 final-holdout, and V4 development/final-holdout disjointness requirements.

Because the corrected eligible pool changes before development scoring, the deterministic development dates may change for an affected group. This is permitted. No outcome information may be used to choose replacements.

## Preservation rule

The previously committed V4 manifest remains part of Git history as evidence of the superseded preflight-invalid membership. The canonical manifest path may be replaced only by a newly generated manifest under the corrected exact-target rule. The new manifest must receive a new canonical content hash and file hash and must pass the governed manifest validator before development scoring.

## Holdout boundary

The V4 final holdout remains sealed. The exact-target availability audit established that all 170 previously selected final-holdout origins have an exact target date, but outcome values remain unread.

## Next gate

`REBUILD_VALIDATE_AND_PRESERVE_V4_MEMBERSHIP_UNDER_EXACT_CALENDAR_TARGET_RULE`
