Crypto Intelligence Platform v12.0.1
Decision Consistency & Allocation Guardrails
=============================================

Corrections
-----------

1. Schema preflight
The recommendation table correctly contains 23 columns.

2. Crypto allocation is a ceiling
The configured 25% crypto exposure is no longer automatically filled.
Cash remains the residual allocation.

3. Action-to-allocation consistency
- STRONG_BUY: may materially increase
- BUY: may increase
- SCALE_IN: may increase gradually
- HOLD: preserve current position; no new capital
- WAIT: preserve current position; no new capital
- REDUCE: lower current exposure
- AVOID: target zero

4. Execution guardrails
HOLD and WAIT cannot produce BUY rows.
A defensive overall decision cannot contain material purchase instructions.

5. Evidence-aware allocation
While Modules 40 and 41 are still accumulating live evidence, eligible buy
allocations are discounted.

6. Confidence-aware allocation
Low forecast confidence reduces deployable target weight.

7. Long-range influence
Long-range scenarios remain available, but low-confidence scenario estimates
do not force capital deployment.

Expected current behavior
-------------------------

Given the reported v12.0 results:

- Overall action should remain REMAIN_DEFENSIVE.
- Bitcoin HOLD should not increase from approximately 0.24% to 8%.
- XRP HOLD should not initiate an 8% position.
- Avalanche WAIT should not initiate a position.
- Solana WAIT should not receive new capital.
- Ethereum and Chainlink may remain HOLD or receive reduction instructions
  only if the action engine explicitly classifies them REDUCE.
- Crypto target weight should remain close to current exposure, not 25%.

Installation
------------

1. Extract into C:\Users\DevonLockard\Crypto
2. Run apply_v12_0_1_decision_guardrails.bat
3. Run python run_module42.py
4. Run python inspect_module42.py
5. Run python export_module42.py
