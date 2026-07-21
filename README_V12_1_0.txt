Crypto Intelligence Platform v12.1.0
Institutional Decision Intelligence
===================================

Module 43 turns Module 42's guarded recommendations into an
investment-committee decision package.

Outputs
-------

1. latest_m43_committee_brief.csv

A one-row executive decision containing:

- Committee decision
- Capital posture
- Review window
- Target crypto and cash percentages
- Highest-ranked opportunity
- Most important change
- Primary risk
- Decision rationale
- Conditions required before deploying capital
- Conditions that require reducing exposure

2. latest_m43_opportunity_ranking.csv

Ranks every asset even when the portfolio remains defensive.

Conviction tiers:

- EXCEPTIONAL
- VERY_HIGH
- HIGH
- MODERATE
- LOW
- VERY_LOW
- NO_EDGE

The ranking combines:

- Investment score
- Forecast confidence
- Reliability
- Medium-term signal
- Risk score

3. latest_m43_decision_changes.csv

Compares the newest successful Module 42 decision with the preceding
successful run:

- Action changes
- Score changes
- Allocation changes
- Confidence changes
- Reliability changes
- 30-day and 3-month median-price changes
- Material or minor change classification

If no prior run exists, the output is BASELINE_CREATED.

4. latest_m43_action_triggers.csv

For every asset, states what must happen before the action improves.

Examples:

- WAIT/HOLD -> SCALE_IN
- SCALE_IN -> BUY
- BUY -> STRONG_BUY

Triggers combine:

- Investment score
- Forecast confidence
- 30-day expected return
- 3-month expected return

It also defines downgrade and reduction conditions.

5. latest_m43_thesis_monitor.csv

Explains:

- Current investment thesis
- Supporting evidence
- Invalidation condition
- Bear-case downside
- Monitoring priority
- Thesis status

6. latest_m43_buy_wait_analysis.csv

Compares:

- Buying now through the 30-day horizon
- Waiting seven days and then holding through day 30
- Waiting 30 days and then holding through month three
- Estimated entry-price advantage from waiting

This is model-based timing analysis, not a guaranteed execution result.

Important
---------

Module 43 does not bypass Module 42.

Module 42 remains the source of:

- Recommended action
- Portfolio allocation
- Entry plan
- Decision consistency guardrails

Module 43 explains, ranks, compares, monitors, and defines conditions.
It cannot create a BUY instruction when Module 42 is HOLD or WAIT.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run install_v12_1_0_windows.bat
3. Run python run_module43.py
4. Run python inspect_module43.py
5. Run python export_module43.py

Recommended workflow
--------------------

For a new decision cycle:

1. Run Module 38
2. Run Module 39
3. Run Module 40
4. Run Module 41
5. Run Module 42
6. Run Module 43

Open these first:

- latest_m43_committee_brief.csv
- latest_m43_opportunity_ranking.csv
- latest_m43_action_triggers.csv
- latest_m43_buy_wait_analysis.csv
