# Focused Crypto Robustness Function Inventory

- Modules inspected: 10
- Relevant functions identified: 107

| Module | Function | Lines | Categories |
|---:|---|---:|---|
| 7 | `__init__` | 254-264 | audit |
| 7 | `modeling_frame` | 277-294 | benchmarks |
| 7 | `score_bins` | 296-326 | audit, benchmarks, calibration |
| 7 | `learned_thresholds` | 328-408 | audit, benchmarks, calibration |
| 7 | `feature_importance` | 410-468 | audit |
| 7 | `walk_forward` | 470-572 | audit, walk_forward |
| 7 | `valuation_validation` | 574-624 | audit, benchmarks |
| 7 | `calibrated_reliability` | 626-671 | audit, benchmarks |
| 7 | `run` | 673-730 | audit, calibration, walk_forward |
| 15 | `annual_metrics` | 168-191 | risk |
| 15 | `__init__` | 194-207 | audit |
| 15 | `rebalance_dates` | 251-270 | benchmarks |
| 15 | `features_at` | 272-364 | benchmarks, risk |
| 15 | `variant_scores` | 366-409 | benchmarks, risk |
| 15 | `allocate` | 411-449 | risk |
| 15 | `simulate` | 461-533 | benchmarks, costs |
| 15 | `objective_score` | 535-558 | benchmarks, costs, risk |
| 15 | `evaluate` | 560-614 | benchmarks, costs, risk |
| 15 | `result_row` | 616-648 | audit, benchmarks, costs, risk |
| 15 | `benchmarks` | 650-699 | audit, benchmarks, risk |
| 15 | `walk_forward_windows` | 701-728 | walk_forward |
| 15 | `aggregate_oos` | 730-757 | benchmarks, risk, walk_forward |
| 15 | `run` | 759-1019 | audit, benchmarks, promotion, risk, walk_forward |
| 23 | `__init__` | 115-121 | audit |
| 23 | `finding` | 126-127 | audit |
| 23 | `source_periods` | 128-131 | audit |
| 23 | `verify` | 135-156 | audit, benchmarks, costs, leakage_protection, risk |
| 23 | `benchmarks` | 157-161 | audit, benchmarks, risk |
| 23 | `attribution` | 162-166 | audit, benchmarks, costs |
| 23 | `labels` | 167-175 | audit, calibration, risk |
| 23 | `bootstrap` | 176-180 | audit, benchmarks, calibration |
| 23 | `summary` | 181-190 | audit, benchmarks, calibration, costs, promotion, risk |
| 23 | `run` | 191-205 | audit, benchmarks, calibration, leakage_protection, promotion, risk |
| 24 | `annual_metrics` | 226-236 | risk |
| 24 | `__init__` | 240-247 | audit |
| 24 | `build_factors` | 285-326 | risk |
| 24 | `generate_candidates` | 328-357 | audit, risk |
| 24 | `allocate` | 373-424 | risk |
| 24 | `simulate` | 426-483 | audit, benchmarks, costs, risk |
| 24 | `evaluate` | 485-503 | benchmarks, costs, risk |
| 24 | `windows` | 505-514 | walk_forward |
| 24 | `walk_forward` | 516-564 | audit, benchmarks, costs, risk, walk_forward |
| 24 | `validate_labels` | 566-608 | audit, benchmarks, calibration, leakage_protection, risk |
| 24 | `aggregate_periods` | 610-622 | benchmarks, costs, risk |
| 24 | `bootstrap` | 624-646 | audit, benchmarks, calibration |
| 24 | `summarize` | 648-712 | audit, benchmarks, calibration, costs, promotion, risk |
| 24 | `run` | 714-767 | audit, benchmarks, calibration, promotion, walk_forward |
| 30 | `confidence_level` | 274-285 | calibration, drift |
| 30 | `__init__` | 289-328 | audit |
| 30 | `data` | 341-380 | audit |
| 30 | `walk_forward` | 382-567 | audit, calibration, walk_forward |
| 30 | `current_model` | 569-685 | calibration, drift, walk_forward |
| 30 | `run` | 687-1055 | audit, benchmarks, calibration, drift, leakage_protection, promotion, walk_forward |
| 32 | `__init__` | 309-335 | audit |
| 32 | `feature_label_data` | 348-364 | audit |
| 32 | `clean_history` | 366-381 | audit, calibration |
| 32 | `feature_stability` | 392-463 | audit, drift |
| 32 | `probability_drift` | 465-500 | audit, calibration, drift |
| 32 | `retraining_policies` | 502-555 | audit, calibration |
| 32 | `historical_stress` | 557-613 | audit, benchmarks, leakage_protection, risk |
| 32 | `synthetic_stress` | 615-659 | audit, benchmarks, calibration, risk |
| 32 | `benchmark` | 661-751 | audit, benchmarks, calibration, costs, leakage_protection, risk |
| 32 | `run` | 753-836 | audit, benchmarks, calibration, drift, risk |
| 33 | `regularize_probabilities` | 266-274 | calibration |
| 33 | `population_stability_index` | 277-305 | drift |
| 33 | `performance_metrics` | 308-365 | costs, risk |
| 33 | `__init__` | 369-394 | audit |
| 33 | `probabilities` | 407-429 | audit, calibration |
| 33 | `disagreement` | 431-446 | audit |
| 33 | `adjusted_drift` | 470-562 | audit, calibration, drift, leakage_protection |
| 33 | `decision_path` | 564-690 | calibration, costs, leakage_protection |
| 33 | `candidate_search` | 692-795 | audit, calibration, costs, risk |
| 33 | `benchmark_rows` | 797-869 | audit, benchmarks, costs, risk |
| 33 | `cost_sensitivity` | 871-920 | audit, benchmarks, costs, risk |
| 33 | `run` | 922-1272 | audit, benchmarks, calibration, costs, drift, risk |
| 38 | `__init__` | 252-287 | audit |
| 38 | `regime_history` | 346-359 | audit |
| 38 | `current_regime` | 361-373 | audit, calibration |
| 38 | `optimizer_expected_returns` | 375-387 | audit |
| 38 | `optimizer_allocations` | 389-401 | audit |
| 38 | `build_features` | 403-462 | leakage_protection, risk |
| 38 | `model_suite` | 464-487 | walk_forward |
| 38 | `train_forecast` | 489-748 | audit, calibration, leakage_protection |
| 38 | `attribution_rows` | 779-846 | audit, risk |
| 38 | `run` | 848-1552 | audit, calibration, costs, risk |
| 40 | `__init__` | 291-324 | audit |
| 40 | `upsert` | 326-450 | audit, calibration |
| 40 | `validate_memory_consistency` | 452-541 | audit, calibration |
| 40 | `recover_interrupted_runs` | 543-559 | audit |
| 40 | `ingest_forecasts` | 561-717 | audit, calibration |
| 40 | `ingest_models` | 719-770 | audit |
| 40 | `ingest_attributions` | 772-822 | audit |
| 40 | `mature_outcomes` | 824-921 | calibration |
| 40 | `learning_summaries` | 923-1136 | audit, calibration, risk |
| 40 | `calibration_curves` | 1138-1215 | audit, calibration |
| 40 | `model_leaderboard` | 1217-1332 | audit |
| 40 | `retraining_recommendations` | 1334-1448 | audit, calibration, drift |
| 40 | `run` | 1450-1724 | audit, calibration, promotion |
| 44 | `__init__` | 232-251 | audit |
| 44 | `recommendations` | 263-267 | audit |
| 44 | `outcomes` | 280-342 | audit |
| 44 | `action_value` | 344-382 | audit |
| 44 | `benchmark_comparison` | 384-421 | audit, benchmarks, risk |
| 44 | `horizon_value` | 423-454 | audit, risk |
| 44 | `timing_value` | 456-502 | audit |
| 44 | `portfolio_value` | 504-534 | audit, benchmarks, risk |
| 44 | `run` | 536-623 | audit, benchmarks |
