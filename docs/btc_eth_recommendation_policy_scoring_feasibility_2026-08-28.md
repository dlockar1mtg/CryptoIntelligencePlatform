# BTC/ETH Recommendation Policy Scoring Feasibility

## Decision date

2026-08-28

## Governing decision

`RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED`

The August 28 maturity gate successfully produced complete exact 7-day
and 30-day forward-outcome coverage for both Bitcoin and Ethereum.

Certification-quality recommendation-policy scoring is nevertheless
**not authorized** because the historical recommendation evidence is
too sparse and concentrated to support a defensible policy-skill claim.

## Bitcoin

- Recommendation rows: 12
- Distinct recommendation dates: 2
- Observed action classes: HOLD, WAIT
- Action counts: {"HOLD": 7, "WAIT": 5}
- Exact 7-day outcomes: 12/12
- Exact 30-day outcomes: 12/12
- Exact 90-day outcomes: 0/12
- Exact 180-day outcomes: 0/12

A bounded descriptive HOLD-versus-WAIT comparison may be performed,
but the twelve stored recommendation rows must not be treated as twelve
independent temporal observations because they represent only two
distinct recommendation dates.

## Ethereum

- Recommendation rows: 12
- Distinct recommendation dates: 2
- Observed action classes: WAIT
- Action counts: {"WAIT": 12}
- Exact 7-day outcomes: 12/12
- Exact 30-day outcomes: 12/12
- Exact 90-day outcomes: 0/12
- Exact 180-day outcomes: 0/12

Ethereum has only WAIT recommendations. No within-asset action-ordering
test is possible from the current historical recommendation record.

## Important maturity conclusion

Waiting for 90-day and 180-day outcomes will increase horizon coverage,
but it will **not** by itself fix the principal certification limitation:
only two independent recommendation dates exist per asset and Ethereum
currently has no action variation.

## Authorized scope

A bounded descriptive 7-day/30-day outcome summary may be performed
for research context if it groups evidence by distinct recommendation
date and does not claim policy certification.

The following remain prohibited:

- certification-quality policy scoring;
- threshold optimization;
- policy-winner selection;
- production recommendation-policy change;
- autonomous execution.

## Final adjudication

Bitcoin:

`INSUFFICIENT_EVIDENCE_FOR_POLICY_SKILL_CERTIFICATION`

Ethereum:

`INSUFFICIENT_EVIDENCE_FOR_POLICY_SKILL_CERTIFICATION`

Overall:

`RECOMMENDATION_POLICY_SKILL_NOT_CERTIFIED`

## Next gate

`CLOSE_BTC_ETH_RECOMMENDATION_POLICY_VALIDATION_AS_INSUFFICIENT_EVIDENCE_AND_PRESERVE_FUTURE_REVISIT`
