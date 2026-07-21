# CRYPTO-ROBUST-001 Strict-Nesting Review

## Final determination

**STATUS: PASS — REMEDIATED**

A follow-up semantic review found that the first CRYPTO-ROBUST-001
remediation prevented outer-test leakage but still selected features
using the complete outer-training frame before separating the inner
validation period.

That residual inner-validation leakage has now been corrected in
Modules 26 and 28.

## Original Module 26 finding

The previous sequence was:

1. Build the complete outer-training frame.
2. Select `fold_sel` using the complete outer-training frame.
3. Split the outer-training frame into `itrain` and `itest`.
4. Tune ensemble candidates using `itrain[fold_sel]` and
   `itest[fold_sel]`.

Because feature selection included rows later used for inner validation,
the inner-validation period influenced feature selection.

## Module 26 remediation

The corrected sequence is:

1. Split outer training into `itrain` and `itest`.
2. Select `inner_sel` using `itrain` only.
3. Tune candidate weights using `itrain[inner_sel]` and
   `itest[inner_sel]`.
4. After inner tuning, select `outer_sel` using the complete
   outer-training frame.
5. Fit and evaluate the selected candidate against the untouched
   outer-test frame using `outer_sel`.
6. Store `outer_sel` in the outer-fold prediction record.

## Original Module 28 finding

The previous sequence selected `fold_retained` from the complete
outer-training frame before splitting that frame into `inner_train`
and `inner_test`.

That allowed inner-validation rows to influence feature retention used
during adaptive candidate search.

## Module 28 remediation

The corrected sequence is:

1. Split outer training into `inner_train` and `inner_test`.
2. Select `inner_retained` using `inner_train` only.
3. Run adaptive search and calibration selection using
   `inner_retained`.
4. After inner tuning, select `outer_retained` using the complete
   outer-training frame.
5. Evaluate selected candidates once against the untouched outer-test
   frame using `outer_retained`.
6. Store `outer_retained` and its count in outer-fold records.

## Verification

Focused tests cover both the existing future-data isolation contract
and the new strict inner/outer selection boundaries.

Results:

- Focused robustness suite: 4 passed
- Complete correction-branch suite: 39 passed
- Compilation checks: passed
- Git whitespace validation: passed

The current branch has three fewer tests than the historical-replay
certification branch because the replay branch alone contains the three
database-path override certification tests.

## Certification impact

- CRYPTO-ROBUST-001 strict nesting: PASS — REMEDIATED
- Outer-test isolation: PASS
- Inner-validation feature-selection isolation: PASS
- Clean historical replay: previously PASS for the pre-remediation code
- New post-remediation replay: still required
- Platform status: RESEARCH ONLY
- Universal integration: BLOCKED pending post-remediation replay