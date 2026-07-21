# Crypto Robustness Capability Audit

This report identifies source-code evidence. It does not by itself
certify that a capability is correctly implemented.

- Modules inspected: 39
- Capability categories: 18
- Evidence records: 264
- Potential leakage findings: 504
- Missing critical capability categories: 0

## Capability coverage

| Capability | Modules with evidence | Critical gate |
|---|---|---|
| `walk_forward_validation` | 7, 8, 9, 15, 16, 19, 20, 21, 22, 24, 26, 27, 28, 29, 30, 38 | Yes |
| `time_based_split` | 7, 8, 9, 15, 16, 19, 22, 24 | Yes |
| `benchmark_comparison` | 6, 11, 14, 15, 16, 20, 21, 22, 23, 24, 27, 30, 32, 33, 34, 35, 37, 44 | Yes |
| `transaction_costs` | 14, 15, 16, 20, 21, 22, 23, 24, 32, 33, 34 | Yes |
| `drawdown_analysis` | 6, 7, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 32, 33, 34, 36, 42, 44 | Yes |
| `risk_adjusted_metrics` | 6, 7, 10, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 44 | Yes |
| `forecast_calibration` | 6, 7, 9, 10, 11, 20, 21, 22, 23, 26, 27, 28, 30, 31, 32, 38, 39, 40, 41 | Yes |
| `statistical_confidence` | 7, 8, 18, 19, 20, 23, 24, 25, 28, 29, 32 | No |
| `regime_validation` | 8, 9, 10, 14, 18, 19, 21, 22, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 40, 42, 43 | No |
| `sensitivity_testing` | 15, 24, 26, 27, 28, 32, 33, 34, 42, 43 | No |
| `feature_drift` | 30, 32, 33 | No |
| `prediction_drift` | 32, 33 | No |
| `performance_drift` | None detected | No |
| `lookahead_protection` | 6, 23, 25, 32, 33, 38 | Yes |
| `deterministic_replay` | 7, 8, 9, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 38 | Yes |
| `auditability` | 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44 | Yes |
| `promotion_guardrails` | 8, 9, 10, 11, 14, 15, 16, 19, 20, 21, 22, 23, 24, 30, 40 | No |
| `universal_contract` | 13, 14, 22, 38, 39, 40, 41, 42, 43, 44 | No |

## Missing critical categories

Source-code evidence was detected for every critical category.

## Potential leakage findings

| Module | Risk type | Line | Source text |
|---:|---|---:|---|
| 6 | `future_named_variable` | 542 | `future_price = None` |
| 6 | `future_named_variable` | 553 | `future_price = float(candidates.iloc[0])` |
| 6 | `future_named_variable` | 555 | `future_price / float(snapshot["price_usd"]) - 1` |
| 6 | `future_named_variable` | 578 | `"future_price_usd": future_price,` |
| 6 | `global_normalization` | 161 | `gain = delta.clip(lower=0).rolling(periods).mean().iloc[-1]` |
| 6 | `global_normalization` | 162 | `loss = -delta.clip(upper=0).rolling(periods).mean().iloc[-1]` |
| 6 | `global_normalization` | 180 | `return float((data / data.cummax() - 1).min() * 100)` |
| 6 | `global_normalization` | 372 | `latest_date = group["observation_date"].max()` |
| 6 | `global_normalization` | 387 | `sma50 = float(hist.tail(50).mean()) if len(hist) >= 50 else None` |
| 6 | `global_normalization` | 388 | `sma200 = float(hist.tail(200).mean()) if len(hist) >= 200 else None` |
| 6 | `global_normalization` | 421 | `price, float(hist.max()), vs200, rsi14, ret90` |
| 6 | `global_normalization` | 523 | `latest_date = prices["observation_date"].max()` |
| 6 | `global_normalization` | 621 | `"positive_rate_pct": float(group["positive_return"].mean() * 100),` |
| 6 | `global_normalization` | 622 | `"average_forward_return_pct": float(group["forward_return_pct"].mean()),` |
| 6 | `global_normalization` | 625 | `float(group["excess_vs_btc_pct"].mean())` |
| 6 | `global_normalization` | 629 | `float(group["outperformed_btc"].mean() * 100)` |
| 7 | `global_normalization` | 207 | `return float(clean.mean()) if not clean.empty else None` |
| 7 | `global_normalization` | 231 | `means = train_values.mean()` |
| 7 | `global_normalization` | 248 | `denominator = float(np.sum((y - y.mean()) ** 2))` |
| 7 | `global_normalization` | 305 | `positive = float(group["positive_return"].mean() * 100)` |
| 7 | `global_normalization` | 318 | `float(group["outperformed_btc"].mean() * 100)` |
| 7 | `global_normalization` | 342 | `score_min = float(eligible["score_bin_low"].min())` |
| 7 | `global_normalization` | 343 | `score_max = float(eligible["score_bin_high"].max())` |
| 7 | `global_normalization` | 482 | `earliest = work["observation_date"].min()` |
| 7 | `global_normalization` | 483 | `latest = work["observation_date"].max()` |
| 7 | `global_normalization` | 525 | `(np.sign(y_test) == np.sign(prediction)).mean() * 100` |
| 7 | `global_normalization` | 535 | `bottom = float(ordered.head(quintile)["actual"].mean())` |
| 7 | `global_normalization` | 536 | `top = float(ordered.tail(quintile)["actual"].mean())` |
| 7 | `global_normalization` | 602 | `positive = float(group["positive_return"].mean() * 100)` |
| 7 | `global_normalization` | 614 | `float(group["outperformed_btc"].mean() * 100)` |
| 8 | `global_normalization` | 340 | `earliest = frame["observation_date"].min()` |
| 8 | `global_normalization` | 341 | `latest = frame["observation_date"].max()` |
| 8 | `global_normalization` | 375 | `(np.sign(y_test) == np.sign(prediction)).mean() * 100` |
| 8 | `global_normalization` | 382 | `bottom = float(ranking.head(quintile)["actual"].mean())` |
| 8 | `global_normalization` | 383 | `top = float(ranking.tail(quintile)["actual"].mean())` |
| 8 | `global_normalization` | 430 | `).mean()` |
| 8 | `global_normalization` | 458 | `float(valid_correlations.mean())` |
| 8 | `global_normalization` | 464 | `fold_frame["directional_accuracy_pct"].mean()` |
| 8 | `global_normalization` | 471 | `fold_frame["top_minus_bottom_pct"].mean()` |
| 8 | `global_normalization` | 477 | `float(fold_frame["mean_absolute_error"].mean())` |
| 8 | `global_normalization` | 587 | `"training_start": frame["observation_date"].min().date(),` |
| 8 | `global_normalization` | 588 | `"training_end": frame["observation_date"].max().date(),` |
| 9 | `global_normalization` | 300 | `frame.tail(size)["actual"].mean()` |
| 9 | `global_normalization` | 301 | `- frame.head(size)["actual"].mean()` |
| 9 | `global_normalization` | 325 | `average = float(group["predicted"].mean())` |
| 9 | `global_normalization` | 326 | `observed = float(group["actual"].mean())` |
| 9 | `global_normalization` | 347 | `earliest = frame["observation_date"].min()` |
| 9 | `global_normalization` | 348 | `latest = frame["observation_date"].max()` |
| 9 | `global_normalization` | 449 | `fold_frame["outperform_auc"].dropna().mean()` |
| 9 | `global_normalization` | 452 | `fold_frame["positive_return_auc"].dropna().mean()` |
| 9 | `global_normalization` | 457 | `].mean()` |
| 9 | `global_normalization` | 462 | `].mean()` |
| 9 | `global_normalization` | 468 | `]].mean(axis=1).mean()` |
| 9 | `global_normalization` | 530 | `group["excess_vs_btc_pct"].mean()` |
| 9 | `global_normalization` | 533 | `group["positive_target"].mean() * 100` |
| 10 | `global_normalization` | 517 | `group["fundingRate"].mean()` |
| 10 | `global_normalization` | 520 | `group["fundingRate"].min()` |
| 10 | `global_normalization` | 523 | `group["fundingRate"].max()` |
| 10 | `global_normalization` | 637 | `latest_date = history["observation_date"].max()` |
| 10 | `global_normalization` | 661 | `current > float(series.tail(50).mean())` |
| 10 | `global_normalization` | 665 | `current > float(series.tail(200).mean())` |
| 10 | `global_normalization` | 802 | `float(data["average_predicted_probability"].min())` |
| 10 | `global_normalization` | 806 | `float(data["average_predicted_probability"].max())` |
| 10 | `global_normalization` | 810 | `float(data["observed_rate"].min())` |
| 10 | `global_normalization` | 814 | `float(data["observed_rate"].max())` |
| 11 | `global_normalization` | 584 | `"first_date": frame["observation_date"].min(),` |
| 11 | `global_normalization` | 585 | `"latest_date": frame["observation_date"].max(),` |
| 11 | `global_normalization` | 662 | `first = history["observation_date"].min()` |
| 11 | `global_normalization` | 663 | `latest = history["observation_date"].max()` |
| 11 | `global_normalization` | 754 | `group["fundingRate"].mean()` |
| 11 | `global_normalization` | 757 | `group["fundingRate"].min()` |
| 11 | `global_normalization` | 760 | `group["fundingRate"].max()` |
| 11 | `global_normalization` | 902 | `float((returns30 > 0).mean() * 100)` |
| 11 | `global_normalization` | 1035 | `].min()) if not data.empty else None` |
| 11 | `global_normalization` | 1040 | `].max()) if not data.empty else None` |
| 12 | `global_normalization` | 110 | `audits.append({'run_id':self.run_id,'asset_id':aid,'source':src,'invalid_epoch_rows':epoch,'invalid_future_rows':future,'duplicate_rows':dup,'rows_removed':removed,'first_valid_date':valid.observation_date.min().date() if not valid.empty el` |
| 12 | `global_normalization` | 170 | `for d,g in f.groupby(f.fundingTime.dt.date): fr.append({'asset_id':m.asset_id,'symbol':m.provider_symbol,'observation_date':d,'average_funding_rate':float(g.fundingRate.mean()),'minimum_funding_rate':float(g.fundingRate.min()),'maximum_fund` |
| 13 | `global_normalization` | 227 | `sma50=float(s.tail(50).mean())` |
| 13 | `global_normalization` | 228 | `sma200=float(s.tail(200).mean()) if len(s)>=200 else None` |
| 13 | `global_normalization` | 233 | `maxdd=float(drawdowns.tail(365).min()*100)` |
| 13 | `global_normalization` | 234 | `recovery=float((current/float(s.tail(365).min())-1)*100) if float(s.tail(365).min())>0 else None` |
| 13 | `global_normalization` | 236 | `atr=float(true_range.mean()*100)` |
| 13 | `global_normalization` | 258 | `annual_return=float(rr.mean()*365)` |
| 13 | `global_normalization` | 418 | `average_score=float(core["overall_score"].mean())` |
| 14 | `future_named_variable` | 404 | `def forward_return(` |
| 14 | `future_named_variable` | 446 | `benchmark_return = self.forward_return(` |
| 14 | `future_named_variable` | 452 | `forward = self.forward_return(` |
| 14 | `future_named_variable` | 463 | `"forward_return": forward,` |
| 14 | `future_named_variable` | 475 | `frame["forward_return"]` |
| 14 | `future_named_variable` | 489 | `row["forward_return"]` |
| 14 | `future_named_variable` | 495 | `row["forward_return"]` |
| 14 | `future_named_variable` | 504 | `row["forward_return"]` |
| 14 | `global_normalization` | 279 | `sma50 = float(s.tail(50).mean())` |
| 14 | `global_normalization` | 280 | `sma200 = float(s.tail(200).mean()) if len(s) >= 200 else None` |
| 14 | `global_normalization` | 306 | `annual_return = float(returns.tail(180).mean() * 365)` |
| 14 | `global_normalization` | 323 | `max_drawdown = float(drawdowns.tail(365).min())` |
| 14 | `global_normalization` | 387 | `end = min(series.index.max() for series in histories.values())` |
| 14 | `global_normalization` | 533 | `].mean()` |
| 14 | `global_normalization` | 536 | `].mean()` |
| 14 | `global_normalization` | 551 | `].mean() * 100` |
| 14 | `global_normalization` | 554 | `group["outperformed_benchmark"].mean()` |
| 14 | `global_normalization` | 561 | `group["forward_return_pct"].mean()` |
| 14 | `global_normalization` | 564 | `group["excess_return_pct"].mean()` |
| 14 | `global_normalization` | 575 | `average_score = float(scores["score"].mean())` |
| 14 | `global_normalization` | 736 | `summary_frame["next_date"].max()` |
| 14 | `global_normalization` | 737 | `- summary_frame["date"].min()` |
| 14 | `global_normalization` | 755 | `maximum_drawdown = float(drawdown.min())` |
| 14 | `global_normalization` | 781 | `).mean() * 100` |
| 14 | `global_normalization` | 796 | `"start_date": summary_frame["date"].min().date(),` |
| 14 | `global_normalization` | 797 | `"end_date": summary_frame["next_date"].max().date(),` |
| 14 | `global_normalization` | 814 | `summary_frame["turnover"].mean() * 100` |
| 14 | `global_normalization` | 820 | `(summary_frame["portfolio_return"] > 0).mean()` |
| 14 | `global_normalization` | 827 | `).mean() * 100` |
| 14 | `global_normalization` | 872 | `).mean() * 100` |
| 14 | `global_normalization` | 874 | `"maximum_drawdown_pct": float(dd.min() * 100),` |
| 15 | `global_normalization` | 190 | `"maximum_drawdown": float(drawdown.min()),` |
| 15 | `global_normalization` | 255 | `end = min(series.index.max() for series in histories.values())` |
| 15 | `global_normalization` | 281 | `sma50 = float(s.tail(50).mean())` |
| 15 | `global_normalization` | 282 | `sma200 = float(s.tail(200).mean()) if len(s) >= 200 else None` |
| 15 | `global_normalization` | 305 | `annual_return = float(returns.tail(180).mean() * 365)` |
| 15 | `global_normalization` | 322 | `max_drawdown = float(drawdown.tail(365).min())` |
| 15 | `global_normalization` | 414 | `average_score = float(scores["score"].mean())` |
| 15 | `global_normalization` | 605 | `(frame["portfolio_return"] > frame["btc_return"]).mean()` |
| 15 | `global_normalization` | 608 | `"average_turnover": float(frame["turnover"].mean()),` |
| 15 | `global_normalization` | 625 | `"start_date": frame["date"].min().date(),` |
| 15 | `global_normalization` | 626 | `"end_date": frame["next_date"].max().date(),` |
| 15 | `global_normalization` | 684 | `"start_date": frame["date"].min().date(),` |
| 15 | `global_normalization` | 685 | `"end_date": frame["next_date"].max().date(),` |
| 15 | `global_normalization` | 748 | `selections["test_information_ratio"].dropna().mean()` |
| 15 | `global_normalization` | 752 | `selections["test_maximum_drawdown_pct"].min() / 100` |
| 15 | `global_normalization` | 755 | `selections["test_benchmark_win_rate_pct"].mean()` |
| 16 | `global_normalization` | 182 | `top=float(df.loc[df.objective_score>=q3,col].mean()); bottom=float(df.loc[df.objective_score<=q1,col].mean())` |
| 17 | `global_normalization` | 335 | `sma = price.rolling(sma_days, min_periods=max(20, sma_days // 2)).mean()` |
| 17 | `global_normalization` | 362 | `mean = series.rolling(365, min_periods=60).mean()` |
| 17 | `global_normalization` | 363 | `std = series.rolling(365, min_periods=60).std().replace(0, np.nan)` |
| 17 | `global_normalization` | 457 | `].mean()` |
| 17 | `global_normalization` | 460 | `].mean()` |
| 17 | `global_normalization` | 475 | `"directional_hit_rate_pct": float(direction.mean() * 100),` |
| 17 | `global_normalization` | 495 | `first = valid_dates.min().date() if len(valid_dates) else None` |
| 17 | `global_normalization` | 496 | `latest = valid_dates.max().date() if len(valid_dates) else None` |
| 17 | `global_normalization` | 498 | `(valid_dates.max() - valid_dates.min()).days + 1` |
| 17 | `global_normalization` | 503 | `float(subset["spearman_correlation"].abs().max())` |
| 18 | `global_normalization` | 57 | `dates=frame.loc[mask,'observation_date']; first=dates.min(); latest=dates.max(); active=(latest-first).days+1; coverage=n/active*100` |
| 18 | `global_normalization` | 59 | `subset=validation[validation['feature_key']==key] if not validation.empty else pd.DataFrame(); best=float(subset['spearman_correlation'].abs().max()) if not subset.empty else 0.0; rules=self.cfg['readiness']` |
| 18 | `global_normalization` | 74 | `za=(sample[a]-sample[a].mean())/sample[a].std(); zb=(sample[b]-sample[b].mean())/sample[b].std()` |
| 18 | `global_normalization` | 76 | `future=sample[target]; corr=signal.rank().corr(future.rank()); lo=signal.quantile(.25); hi=signal.quantile(.75); top=future[signal>=hi].mean(); bottom=future[signal<=lo].mean()` |
| 18 | `global_normalization` | 91 | `sma=frame['btc_price_usd'].rolling(int(self.cfg['regimes']['sma_days']),min_periods=100).mean(); momentum=frame['btc_price_usd'].pct_change(int(self.cfg['regimes']['momentum_days']),fill_method=None); sample=frame.copy(); sample['regime']=n` |
| 18 | `global_normalization` | 98 | `future=group[target]; corr=group[key].rank().corr(future.rank()); median=group[key].median(); hit=(((group[key]-median)*future)>0).mean()*100; lo=group[key].quantile(.25); hi=group[key].quantile(.75); spread=future[group[key]>=hi].mean()-fu` |
| 19 | `global_normalization` | 304 | `].mean()` |
| 19 | `global_normalization` | 307 | `].mean()` |
| 19 | `global_normalization` | 316 | `).mean() * 100` |
| 19 | `global_normalization` | 351 | `first = frame["observation_date"].min()` |
| 19 | `global_normalization` | 352 | `last = frame["observation_date"].max()` |
| 19 | `global_normalization` | 440 | `].mean()` |
| 19 | `global_normalization` | 443 | `].mean()` |
| 19 | `global_normalization` | 451 | `).mean() * 100` |
| 19 | `global_normalization` | 722 | `].abs().max()` |
| 19 | `global_normalization` | 746 | `roll["sign_consistent"].mean()` |
| 19 | `global_normalization` | 754 | `roll["testing_spearman"].mean()` |
| 19 | `global_normalization` | 786 | `float(perm["importance_mean"].max())` |
| 20 | `global_normalization` | 194 | `return total,ann,vol,(ann/vol if vol>0 else None),(float(dd.min()) if len(dd) else 0.0)` |
| 20 | `global_normalization` | 234 | `r2=float(r2_score(test[target],pred)); mae=float(mean_absolute_error(test[target],pred)); direction=float((np.sign(pred)==np.sign(test[target])).mean()*100); rank=float(pd.Series(pred).rank().corr(test[target].reset_index(drop=True).rank())` |
| 20 | `global_normalization` | 265 | `mean=float(s.testing_spearman.mean()) if len(s) else 0.0; consistency=float(s.sign_consistent.mean()*100) if len(s) else 0.0` |
| 20 | `global_normalization` | 294 | `std=s.std(); z=0.0 if not std or pd.isna(std) else float((s.iloc[-1]-s.mean())/std); signals.append(np.clip(z,-2,2)*directions.get(x,1.0))` |
| 20 | `global_normalization` | 303 | `summary=pd.DataFrame([{'run_id':self.run_id,'start_date':periods.rebalance_date.min(),'end_date':periods.next_rebalance_date.max(),'periods':len(periods),'promoted_feature_count':len(features),'total_return_pct':p[0]*100,'annualized_return_` |
| 21 | `future_named_variable` | 438 | `evaluated["forward_return"] = (` |
| 21 | `future_named_variable` | 462 | `"POSITIVE_RETURN": (evaluated["forward_return"] > 0).astype(float),` |
| 21 | `future_named_variable` | 855 | `next_price = float(btc.iloc[next_index])` |
| 21 | `future_named_variable` | 856 | `btc_return = next_price / current_price - 1` |
| 21 | `global_normalization` | 272 | `return total, annual, volatility, sharpe, float(drawdown.min())` |
| 21 | `global_normalization` | 361 | `mean = series.rolling(window, min_periods=minimum).mean()` |
| 21 | `global_normalization` | 362 | `std = series.rolling(window, min_periods=minimum).std().replace(0, np.nan)` |
| 21 | `global_normalization` | 367 | `sma200 = btc.rolling(200, min_periods=120).mean()` |
| 21 | `global_normalization` | 585 | `latest_date = prices.index.max()` |
| 21 | `global_normalization` | 590 | `cvar95 = float(cvar_values.mean() * 100) if not cvar_values.empty else var95` |
| 21 | `global_normalization` | 593 | `maximum_drawdown = float(drawdown.min() * 100)` |
| 21 | `global_normalization` | 910 | `(portfolio_returns > btc_returns).mean() * 100` |
| 21 | `global_normalization` | 923 | `"start_date": periods["rebalance_date"].min(),` |
| 21 | `global_normalization` | 924 | `"end_date": periods["next_rebalance_date"].max(),` |
| 21 | `global_normalization` | 936 | `"average_btc_weight_pct": float(periods["btc_weight"].mean() * 100),` |
| 21 | `global_normalization` | 937 | `"average_turnover_pct": float(periods["turnover_pct"].mean()),` |
| 22 | `future_named_variable` | 454 | `future_return = btc.shift(-int(horizon)) / btc - 1` |
| 22 | `future_named_variable` | 461 | `positive_target = (future_return > 0).astype(float).where(` |
| 22 | `future_named_variable` | 462 | `future_return.notna(), float("nan")` |
| 22 | `global_normalization` | 250 | `return total, annual, vol, sharpe, float(dd.min())` |
| 22 | `global_normalization` | 318 | `output["btc_distance_sma50_pct"] = (btc / btc.rolling(50).mean() - 1) * 100` |
| 22 | `global_normalization` | 319 | `output["btc_distance_sma200_pct"] = (btc / btc.rolling(200).mean() - 1) * 100` |
| 22 | `global_normalization` | 321 | `returns["bitcoin"].rolling(30).std() * math.sqrt(365) * 100` |
| 22 | `global_normalization` | 324 | `returns["bitcoin"].rolling(90).std() * math.sqrt(365) * 100` |
| 22 | `global_normalization` | 367 | `mean = series.rolling(window, min_periods=minimum).mean()` |
| 22 | `global_normalization` | 368 | `std = series.rolling(window, min_periods=minimum).std().replace(0, np.nan)` |
| 22 | `global_normalization` | 413 | `coverage = combined.notna().mean().sort_values(ascending=False)` |
| 22 | `global_normalization` | 584 | `vol90 = ret.tail(90).std() * math.sqrt(365) * 100` |
| 22 | `global_normalization` | 659 | `start = max(price.index.min(), expanded.index.min()) + pd.DateOffset(months=train_months)` |
| 22 | `global_normalization` | 660 | `last = min(price.index.max(), expanded.index.max())` |
| 22 | `global_normalization` | 743 | `max_dd = float((dd / dd.cummax() - 1).min())` |
| 22 | `global_normalization` | 745 | `ir = float((pr.mean() - br.mean()) / active.std(ddof=1) * math.sqrt(365 / int(self.cfg["portfolio"]["rebalance_days"]))) if len(active) > 1 and active.std(ddof=1) > 0 else None` |
| 22 | `global_normalization` | 822 | `"start_date": grouped["rebalance_date"].min(),` |
| 22 | `global_normalization` | 823 | `"end_date": grouped["next_rebalance_date"].max(),` |
| 22 | `global_normalization` | 834 | `"benchmark_win_rate_pct": float((pr > br).mean() * 100),` |
| 22 | `global_normalization` | 835 | `"average_cash_weight_pct": float(grouped["cash_actual"].mean() * 100),` |
| 22 | `global_normalization` | 836 | `"average_turnover_pct": float(grouped["turnover_pct"].mean()),` |
| 23 | `global_normalization` | 112 | `sh=ann/vol if vol>0 else None; dd=float((c/c.cummax()-1).min()) if len(c) else 0.0` |
| 23 | `global_normalization` | 145 | `stored_min=float(g['portfolio_period_return_pct'].min()); stored_max=float(g['portfolio_period_return_pct'].max()); err=stored_max-corrected` |
| 23 | `global_normalization` | 150 | `btc=realized['bitcoin']; eq=float(np.nanmean(list(realized.values()))); trailing=price.loc[:d].pct_change(fill_method=None).tail(90); vol=trailing[CORE].std().replace(0,np.nan); iw=(1/vol); iw=iw/iw.sum(); iv=float(sum(iw.get(a,0)*realized[` |
| 23 | `global_normalization` | 160 | `t,a,v,s,d=metrics(p[col]/100,ppy); rows.append(dict(run_id=self.run_id,benchmark_name=n,start_date=p.rebalance_date.min(),end_date=p.next_rebalance_date.max(),periods=len(p),total_return_pct=t*100,annualized_return_pct=a*100,annualized_vola` |
| 23 | `global_normalization` | 165 | `for k,s,e in [('MARKET_EXPOSURE',market,'Risky exposure applied to BTC return.'),('DIVERSIFICATION_AND_SELECTION',selection,'Asset selection and diversification versus BTC exposure.'),('CASH_TIMING',cash,'Effect of holding less than 100% BT` |
| 23 | `global_normalization` | 180 | `return pd.DataFrame([dict(run_id=self.run_id,simulations=sims,seed=seed,mean_excess_return_pct=float(ex.mean()),median_excess_return_pct=float(np.median(ex)),lower_95_pct=float(np.quantile(ex,.025)),upper_95_pct=float(np.quantile(ex,.975)),` |
| 23 | `global_normalization` | 190 | `return pd.DataFrame([dict(run_id=self.run_id,source_module22_run_id=self.source,start_date=p.rebalance_date.min(),end_date=p.next_rebalance_date.max(),periods=len(p),stored_total_return_pct=stored,corrected_total_return_pct=t*100,corrected_` |
| 24 | `global_normalization` | 236 | `return total, annual, volatility, sharpe, float(drawdown.min())` |
| 24 | `global_normalization` | 311 | `"trend_50_200": series.rolling(50).mean() / series.rolling(200).mean() - 1,` |
| 24 | `global_normalization` | 313 | `"realized_volatility_90d": ret.rolling(90).std() * math.sqrt(365),` |
| 24 | `global_normalization` | 314 | `"max_drawdown_180d": series / series.rolling(180).max() - 1,` |
| 24 | `global_normalization` | 364 | `return ((series - series.mean()) / std).clip(-3, 3)` |
| 24 | `global_normalization` | 370 | `latest = pd.to_datetime(eligible["observation_date"]).max()` |
| 24 | `global_normalization` | 404 | `+ max(0.0, -safe(score.mean())) * candidate["cash_sensitivity"] * 0.18` |
| 24 | `global_normalization` | 409 | `raw = np.exp((score.fillna(score.median()) - score.max()) * 0.8)` |
| 24 | `global_normalization` | 448 | `trailing_vol = price.loc[:date].pct_change(fill_method=None).tail(90)[CORE_IDS].std().replace(0, np.nan)` |
| 24 | `global_normalization` | 496 | `objective = p[1] * 30 + (ir if ir is not None else -1) * 18 + p[4] * 20 + (frame["portfolio_return"] > frame["btc_return"]).mean() * 12 - frame["turnover"].mean() * 20` |
| 24 | `global_normalization` | 500 | `"tracking": tracking, "ir": ir, "cash": frame["cash_weight"].mean(),` |
| 24 | `global_normalization` | 501 | `"turnover": frame["turnover"].mean(), "cost": frame["transaction_cost"].sum(),` |
| 24 | `global_normalization` | 509 | `test_start = price.index.min() + pd.DateOffset(months=train_months)` |
| 24 | `global_normalization` | 511 | `while test_start + pd.DateOffset(months=test_months) <= price.index.max():` |
| 24 | `global_normalization` | 599 | `"event_rate_pct": sample["target"].mean() * 100,` |
| 24 | `global_normalization` | 662 | `reconciliation = float(aggregated["reconciliation_error_pct"].abs().max())` |
| 24 | `global_normalization` | 685 | `"start_date": aggregated["rebalance_date"].min(),` |
| 24 | `global_normalization` | 686 | `"end_date": aggregated["next_rebalance_date"].max(),` |
| 24 | `global_normalization` | 700 | `"benchmark_win_rate_pct": float((portfolio > btc).mean() * 100),` |
| 24 | `global_normalization` | 701 | `"average_cash_weight_pct": float(results[results["selected_for_fold"]]["average_cash_weight_pct"].mean()),` |
| 24 | `global_normalization` | 702 | `"average_turnover_pct": float(aggregated["turnover_pct"].mean()),` |
| 25 | `global_normalization` | 318 | `mean = series.rolling(window, min_periods=120).mean()` |
| 25 | `global_normalization` | 319 | `std = series.rolling(window, min_periods=120).std().replace(0, np.nan)` |
| 25 | `global_normalization` | 370 | `btc / btc.rolling(50).mean() - 1` |
| 25 | `global_normalization` | 373 | `btc / btc.rolling(200).mean() - 1` |
| 25 | `global_normalization` | 376 | `returns["bitcoin"].rolling(30).std()` |
| 25 | `global_normalization` | 380 | `returns["bitcoin"].rolling(90).std()` |
| 25 | `global_normalization` | 384 | `btc / btc.rolling(180).max() - 1` |
| 25 | `global_normalization` | 1035 | `probabilities["regime_confidence"].mean()` |
| 25 | `global_normalization` | 1041 | `).mean()` |
| 25 | `global_normalization` | 1044 | `probabilities["model_agreement"].mean()` |
| 25 | `global_normalization` | 1052 | `].mean()` |
| 26 | `full_sample_scaler_fit` | 122 | `j=f[cols].join(l['dominant_regime']).dropna(); y=j['dominant_regime'].map({r:i for i,r in enumerate(REGIMES)}).astype(int); X=j[cols]; mi=mutual_info_classif(StandardScaler().fit_transform(X),y,random_state=int(self.cfg['models']['random_st` |
| 26 | `global_normalization` | 95 | `return [c for c in f.columns if c not in skip and pd.api.types.is_numeric_dtype(f[c]) and f[c].notna().mean()>=float(self.cfg['feature_selection']['minimum_coverage'])]` |
| 26 | `global_normalization` | 124 | `med=X[c].rolling(180,min_periods=90).median(); pred=np.where(X[c]>=med,1,0); target=y.isin([0,1,2]).astype(int); valid=~pd.isna(med); agr=float((pred[valid]==target[valid]).mean()*100) if valid.any() else 0; stab=float(100*(1-X[c].diff().ab` |
| 26 | `global_normalization` | 155 | `agr=accuracy_score(itest['dominant_regime'],labs)*100; raw=np.array([p.max() for p in ps]); correct=np.array([a==b for a,b in zip(itest['dominant_regime'],labs)],float); mae=float(np.mean(np.abs(raw-correct))); obj=agr-mae*40; scored.append` |
| 26 | `global_normalization` | 159 | `for comp,actual in zip(comps,itest['dominant_regime']): p=self.combine(comp,best[1],prev); prev=p; lab=REGIMES[int(np.argmax(p))]; raw.append(float(p.max())); corr.append(float(lab==actual))` |
| 26 | `global_normalization` | 164 | `p=self.combine(comp,best[1],prev); prev=p; lab=REGIMES[int(np.argmax(p))]; rc=float(p.max()); cc=float(iso.predict([rc])[0]) if iso is not None else rc` |
| 26 | `global_normalization` | 165 | `preds.append({'run_id':self.run_id,'outer_fold':fold,'observation_date':date.date(),'training_start_date':train.index.min().date(),'training_end_date':train.index.max().date(),'testing_start_date':test.index.min().date(),'testing_end_date':` |
| 26 | `global_normalization` | 172 | `raw=float(g['raw_confidence'].mean()); cal=float(g['calibrated_confidence'].mean()); obs=float(g['correct'].mean()); rows.append({'run_id':self.run_id,'confidence_bin':str(label),'observations':len(g),'mean_raw_confidence':raw,'mean_calibra` |
| 26 | `global_normalization` | 175 | `base=float(p['label_match'].mean()*100) if not p.empty else 0; cur=p.iloc[-1] if not p.empty else None; scenarios=[('FEATURE_MINUS_1',max(len(sel)-1,3),0,0),('FEATURE_PLUS_1',len(sel)+1,0,0),('SMOOTHING_MINUS_05',len(sel),-.05,0),('SMOOTHIN` |
| 26 | `global_normalization` | 184 | `agr=float(pred['label_match'].mean()*100) if not pred.empty else 0; raw=float(cal['raw_absolute_error'].mean()) if not cal.empty else 1; mae=float(cal['calibrated_absolute_error'].mean()) if not cal.empty else 1; stability=float(sens['label` |
| 27 | `global_normalization` | 218 | `logits -= logits.max()` |
| 27 | `global_normalization` | 306 | `short_vol = btc.rolling(30).std() * math.sqrt(365)` |
| 27 | `global_normalization` | 307 | `long_vol = btc.rolling(90).std() * math.sqrt(365)` |
| 27 | `global_normalization` | 308 | `negative_share = (returns["bitcoin"] < 0).rolling(30).mean()` |
| 27 | `global_normalization` | 424 | `scores -= scores.max()` |
| 27 | `global_normalization` | 451 | `scores -= scores.max()` |
| 27 | `global_normalization` | 570 | `confidence = np.array([p.max() for p in probabilities])` |
| 27 | `global_normalization` | 574 | `agreement = float(correct.mean()*100)` |
| 27 | `global_normalization` | 652 | `raw_inner = np.array([p.max() for p in best_inner["probabilities"]])` |
| 27 | `global_normalization` | 681 | `raw = float(p.max())` |
| 27 | `global_normalization` | 697 | `"training_start_date": train.index.min().date(),` |
| 27 | `global_normalization` | 698 | `"training_end_date": train.index.max().date(),` |
| 27 | `global_normalization` | 699 | `"testing_start_date": test.index.min().date(),` |
| 27 | `global_normalization` | 700 | `"testing_end_date": test.index.max().date(),` |
| 27 | `global_normalization` | 713 | `"testing_start_date": test.index.min().date(),` |
| 27 | `global_normalization` | 714 | `"testing_end_date": test.index.max().date(),` |
| 27 | `global_normalization` | 718 | `np.mean([p.max() for p in outer_result["probabilities"]])` |
| 27 | `global_normalization` | 746 | `raw = float(group["raw_confidence"].mean())` |
| 27 | `global_normalization` | 747 | `cal = float(group["calibrated_confidence"].mean())` |
| 27 | `global_normalization` | 748 | `observed = float(group["correct"].mean())` |
| 27 | `global_normalization` | 806 | `agreement = float(predictions["label_match"].mean()*100)` |
| 27 | `global_normalization` | 811 | `== indexed.loc[common,"predicted_regime"]).mean()*100` |
| 27 | `global_normalization` | 860 | `agreement = float(predictions["label_match"].mean()*100)` |
| 27 | `global_normalization` | 861 | `raw_mae = float(calibration["raw_error"].mean()) if not calibration.empty else 1.0` |
| 27 | `global_normalization` | 863 | `float(calibration["calibrated_error"].mean())` |
| 27 | `global_normalization` | 870 | `float(nonbaseline["agreement_with_baseline_pct"].mean())` |
| 28 | `full_sample_scaler_fit` | 589 | `reduced_scaled = StandardScaler().fit_transform(x[reduced])` |
| 28 | `global_normalization` | 235 | `logits -= logits.max()` |
| 28 | `global_normalization` | 330 | `scores -= scores.max()` |
| 28 | `global_normalization` | 360 | `means[regime] = group.mean().to_numpy()` |
| 28 | `global_normalization` | 376 | `x -= x.max()` |
| 28 | `global_normalization` | 452 | `confidence = np.array([p.max() for p in probabilities])` |
| 28 | `global_normalization` | 453 | `agreement = float(correctness.mean()*100)` |
| 28 | `global_normalization` | 578 | `float(corr.loc[feature].drop(feature).nlargest(3).mean())` |
| 28 | `global_normalization` | 582 | `grouped_means = x.groupby(y)[feature].mean()` |
| 28 | `global_normalization` | 584 | `grouped_means.std()` |
| 28 | `global_normalization` | 585 | `/ max(x[feature].std(), 1e-9)` |
| 28 | `global_normalization` | 724 | `(objectives-objectives.max())` |
| 28 | `global_normalization` | 764 | `inner_raw = np.array([p.max() for p in inner_meta])` |
| 28 | `global_normalization` | 818 | `raw_values = np.array([p.max() for p in outer_probabilities])` |
| 28 | `global_normalization` | 838 | `"training_start_date": train.index.min().date(),` |
| 28 | `global_normalization` | 839 | `"training_end_date": train.index.max().date(),` |
| 28 | `global_normalization` | 840 | `"testing_start_date": test.index.min().date(),` |
| 28 | `global_normalization` | 841 | `"testing_end_date": test.index.max().date(),` |
| 28 | `global_normalization` | 862 | `"testing_start_date": test.index.min().date(),` |
| 28 | `global_normalization` | 863 | `"testing_end_date": test.index.max().date(),` |
| 28 | `global_normalization` | 867 | `"agreement_pct": float(correctness.mean()*100),` |
| 28 | `global_normalization` | 926 | `).mean()*100)` |
| 28 | `global_normalization` | 938 | `"agreement_pct": float(correctness.mean()*100),` |
| 28 | `global_normalization` | 973 | `predictions["label_match"].mean()*100` |
| 28 | `global_normalization` | 987 | `float(nonprimary["agreement_with_primary_pct"].mean())` |
| 29 | `global_normalization` | 362 | `if frame[c].notna().mean() >= minimum_coverage` |
| 29 | `global_normalization` | 451 | `"training_start_date": train.index.min().date(),` |
| 29 | `global_normalization` | 452 | `"training_end_date": train.index.max().date(),` |
| 29 | `global_normalization` | 453 | `"testing_start_date": test.index.min().date(),` |
| 29 | `global_normalization` | 454 | `"testing_end_date": test.index.max().date(),` |
| 29 | `global_normalization` | 627 | `"window_start_date": window.index.min().date(),` |
| 29 | `global_normalization` | 628 | `"window_end_date": window.index.max().date(),` |
| 29 | `global_normalization` | 658 | `float(frame[feature].std()),` |
| 29 | `global_normalization` | 662 | `float(in_regime[feature].mean())` |
| 29 | `global_normalization` | 663 | `- float(out_regime[feature].mean())` |
| 29 | `global_normalization` | 666 | `in_regime[feature].std()` |
| 29 | `global_normalization` | 742 | `)["regime_separation_score"].mean()` |
| 29 | `global_normalization` | 755 | `.mean()` |
| 29 | `global_normalization` | 840 | `frame[feature].notna().mean() * 100` |
| 29 | `global_normalization` | 1241 | `].max()` |
| 30 | `global_normalization` | 491 | `"training_start_date": training.index.min().date(),` |
| 30 | `global_normalization` | 492 | `"training_end_date": training.index.max().date(),` |
| 30 | `global_normalization` | 493 | `"testing_start_date": testing.index.min().date(),` |
| 30 | `global_normalization` | 494 | `"testing_end_date": testing.index.max().date(),` |
| 30 | `global_normalization` | 723 | `history["label_match"].mean() * 100` |
| 31 | `global_normalization` | 258 | `mean=float(s.mean()*100); asset_means.append(mean); positive_assets.append(mean>0)` |
| 31 | `global_normalization` | 259 | `std=float(s.std())` |
| 31 | `global_normalization` | 260 | `ir=float((s.mean()/std)*math.sqrt(365/horizon)) if std>0 else 0.0` |
| 31 | `global_normalization` | 261 | `rows.append({'run_id':self.run_id,'signal_source':source,'regime':regime,'asset_id':asset,'horizon_days':horizon,'observations':len(s),'mean_forward_return_pct':mean,'median_forward_return_pct':float(s.median()*100),'positive_return_rate_pc` |
| 31 | `global_normalization` | 263 | `btc=float(forward.loc[mask,'bitcoin'].dropna().mean()*100) if 'bitcoin' in forward else 0` |
| 31 | `global_normalization` | 264 | `alt_cols=[c for c in prices.columns if c!='bitcoin']; alt=float(forward.loc[mask,alt_cols].stack().mean()*100)` |
| 31 | `global_normalization` | 278 | `rows.append({'run_id':self.run_id,'disagreement_group':group,'horizon_days':horizon,'observations':int(mask.sum()),'btc_mean_return_pct':float(btc.mean()*100),'alt_mean_return_pct':float(alt.mean()*100),'positive_btc_rate_pct':float((btc>0)` |
| 31 | `global_normalization` | 286 | `absmean=float(g['probability_contribution'].abs().mean())` |
| 31 | `global_normalization` | 287 | `rows.append({'run_id':self.run_id,'feature_key':feature,'mean_absolute_contribution':absmean,'contribution_std':float(g['probability_contribution'].std() or 0),'positive_support_rate_pct':float((g['probability_contribution']>0).mean()*100),` |
| 31 | `global_normalization` | 324 | `clean_sep=float(scorecard.loc[scorecard.signal_source=='CLEAN','economic_separation_score'].mean())` |
| 31 | `global_normalization` | 325 | `legacy_sep=float(scorecard.loc[scorecard.signal_source=='LEGACY','economic_separation_score'].mean())` |
| 31 | `global_normalization` | 328 | `disagreement_value=float((pivot.get('DISAGREE',pd.Series(dtype=float))-pivot.get('AGREE',pd.Series(dtype=float))).abs().mean())` |
| 32 | `global_normalization` | 419 | `mean_rank=float(abs_rank[feature].mean())` |
| 32 | `global_normalization` | 420 | `rank_persistence=float((abs_rank[feature]<=3).mean()*100)` |
| 32 | `global_normalization` | 422 | `absmean=float(values.abs().mean())` |
| 32 | `global_normalization` | 431 | `"training_start_date":train.index.min().date(),` |
| 32 | `global_normalization` | 432 | `"training_end_date":train.index.max().date(),` |
| 32 | `global_normalization` | 433 | `"testing_start_date":test.index.min().date(),` |
| 32 | `global_normalization` | 434 | `"testing_end_date":test.index.max().date(),` |
| 32 | `global_normalization` | 438 | `"positive_support_rate_pct":float((values>0).mean()*100),` |
| 32 | `global_normalization` | 439 | `"negative_support_rate_pct":float((values<0).mean()*100),` |
| 32 | `global_normalization` | 450 | `score=float(g["stability_score"].mean())` |
| 32 | `global_normalization` | 453 | `"mean_absolute_contribution":float(g["mean_absolute_contribution"].mean()),` |
| 32 | `global_normalization` | 455 | `"positive_support_rate_pct":float(g["positive_support_rate_pct"].mean()),` |
| 32 | `global_normalization` | 456 | `"sign_flip_rate_pct":float(g["sign_flip_rate_pct"].mean()),` |
| 32 | `global_normalization` | 457 | `"mean_rank":float(g["mean_rank"].mean()),` |
| 32 | `global_normalization` | 458 | `"rank_persistence_pct":float(g["rank_persistence_pct"].mean()),` |
| 32 | `global_normalization` | 482 | `disagreement=float((h["model_agreement"]<.55).mean()*100)` |
| 32 | `global_normalization` | 489 | `"run_id":self.run_id,"window_end_date":block.index.max().date(),` |
| 32 | `global_normalization` | 491 | `"mean_top_probability":float(block.max(axis=1).mean()),` |
| 32 | `global_normalization` | 492 | `"mean_entropy":float(entropy(block.to_numpy()).mean()),` |
| 32 | `global_normalization` | 544 | `"mean_top_probability":float(matrix.max(axis=1).mean()),` |
| 32 | `global_normalization` | 560 | `vol=ret.rolling(30).std()*math.sqrt(365)` |
| 32 | `global_normalization` | 590 | `dd=float((segment/segment.cummax()-1).min()*100)` |
| 32 | `global_normalization` | 593 | `+min(float(p.max(axis=1).mean()*100),100)*.25` |
| 32 | `global_normalization` | 604 | `"mean_clean_confidence":float(p.max(axis=1).mean()),` |
| 32 | `global_normalization` | 631 | `std=float(train[feature].std())` |
| 32 | `global_normalization` | 681 | `vol=returns.rolling(90,min_periods=30).std().replace(0,np.nan)` |
| 32 | `global_normalization` | 684 | `btc_vol=returns["bitcoin"].rolling(30,min_periods=20).std()*math.sqrt(365)` |
| 32 | `global_normalization` | 716 | `vol_ann=float(strategy_return.std()*math.sqrt(365))` |
| 32 | `global_normalization` | 717 | `sharpe=float(strategy_return.mean()/strategy_return.std()*math.sqrt(365)) if strategy_return.std()>0 else 0` |
| 32 | `global_normalization` | 718 | `downside=strategy_return[strategy_return<0].std()` |
| 32 | `global_normalization` | 719 | `sortino=float(strategy_return.mean()/downside*math.sqrt(365)) if downside and downside>0 else 0` |
| 32 | `global_normalization` | 721 | `maxdd=float(dd.min())` |
| 32 | `global_normalization` | 724 | `cvar=float(strategy_return[strategy_return<=q].mean())` |
| 32 | `global_normalization` | 733 | `"profitable_months_pct":float((monthly>0).mean()*100),` |
| 32 | `global_normalization` | 734 | `"annualized_turnover_pct":float(turnover.mean()*365*100),` |
| 32 | `global_normalization` | 788 | `stress_pass=float(synthetic["monotonic_passed"].mean()*100)` |
| 32 | `global_normalization` | 789 | `mean_stability=float(stability_summary["stability_score"].mean())` |
| 33 | `global_normalization` | 319 | `volatility = float(strategy_return.std() * math.sqrt(365))` |
| 33 | `global_normalization` | 322 | `strategy_return.mean()` |
| 33 | `global_normalization` | 323 | `/ strategy_return.std()` |
| 33 | `global_normalization` | 326 | `if strategy_return.std() > 0` |
| 33 | `global_normalization` | 329 | `downside = strategy_return[strategy_return < 0].std()` |
| 33 | `global_normalization` | 332 | `strategy_return.mean()` |
| 33 | `global_normalization` | 342 | `maximum_drawdown = float(drawdown.min())` |
| 33 | `global_normalization` | 360 | `turnover.mean() * 365 * 100` |
| 33 | `global_normalization` | 516 | `actual_top.mean()` |
| 33 | `global_normalization` | 517 | `/ max(reference_top.mean(), 1e-9)` |
| 33 | `global_normalization` | 526 | `(block_agreement < .55).mean() * 100` |
| 33 | `global_normalization` | 543 | `"window_end_date": actual.index.max().date(),` |
| 33 | `global_normalization` | 548 | `actual_top.mean()` |
| 33 | `global_normalization` | 551 | `actual_entropy.mean()` |
| 33 | `global_normalization` | 650 | `probabilities.loc[date].max()` |
| 33 | `global_normalization` | 1087 | `cost_sensitivity["passed"].mean() * 100` |
| 34 | `global_normalization` | 242 | `vol=float(returns.std()*math.sqrt(365))` |
| 34 | `global_normalization` | 243 | `sharpe=float(returns.mean()/returns.std()*math.sqrt(365)) if returns.std()>0 else 0.0` |
| 34 | `global_normalization` | 244 | `downside=returns[returns<0].std()` |
| 34 | `global_normalization` | 245 | `sortino=float(returns.mean()/downside*math.sqrt(365)) if downside is not None and not pd.isna(downside) and downside>0 else 0.0` |
| 34 | `global_normalization` | 247 | `maxdd=float(drawdown.min())` |
| 34 | `global_normalization` | 258 | `"annualized_turnover_pct":float(turnover.mean()*365*100),` |
| 34 | `global_normalization` | 516 | `disagree=float((disagreement.reindex(actual.index)<.55).mean()*100)` |
| 34 | `global_normalization` | 533 | `"window_end_date":actual.index.max().date(),` |
| 34 | `global_normalization` | 679 | `pass_rate=float(costs["passed"].mean()*100)` |
| 35 | `global_normalization` | 63 | `mu=r.mean().to_numpy()*365; cov=r.cov().to_numpy()*365; vol=np.sqrt(np.clip(np.diag(cov),1e-12,None)); risk=float(ex['target_risk_exposure'])` |
| 36 | `global_normalization` | 52 | `a=self.conn.execute("SELECT observation_date,asset_id,final_target_weight FROM m35_portfolio_allocations WHERE run_id=?",[self.source]).fetchdf(); a['observation_date']=pd.to_datetime(a['observation_date']); date=a.observation_date.max().da` |
| 36 | `global_normalization` | 55 | `xret=r[x]; xv=float(xret.std()*math.sqrt(365)); xv95=float(xret.quantile(.05)); xc=float(xret[xret<=xv95].mean()); xcum=(1+xret).cumprod(); xdd=xcum/xcum.cummax()-1; status='HIGH' if xv>.8 else 'MODERATE' if xv>.5 else 'LOW'; ar.append({'ru` |
| 37 | `global_normalization` | 353 | `observation_date = frame["observation_date"].max()` |
| 37 | `global_normalization` | 385 | `historical = sample.mean() * 365` |
| 37 | `global_normalization` | 924 | `weights.max()` |
| 37 | `global_normalization` | 927 | `weights.min()` |
| 37 | `global_normalization` | 1127 | `active_return.std()` |
| 37 | `global_normalization` | 1138 | `active_return.mean()` |
| 38 | `global_normalization` | 428 | `returns.rolling(30).std()` |
| 38 | `global_normalization` | 432 | `returns.rolling(90).std()` |
| 38 | `global_normalization` | 436 | `price / price.rolling(50).mean() - 1` |
| 38 | `global_normalization` | 439 | `price / price.rolling(200).mean() - 1` |
| 38 | `global_normalization` | 674 | `weight == weights.max()` |
| 38 | `global_normalization` | 908 | `].max()` |
| 38 | `global_normalization` | 1032 | `).std().iloc[-1]` |
| 38 | `global_normalization` | 1038 | `).std().iloc[-1]` |
| 38 | `global_normalization` | 1045 | `).mean().iloc[-1]` |
| 38 | `global_normalization` | 1052 | `).mean().iloc[-1]` |
| 38 | `global_normalization` | 1422 | `transition_probability.max()` |
| 38 | `global_normalization` | 1517 | `transition_probability.max()` |
| 39 | `global_normalization` | 288 | `directional.mean()` |
| 39 | `global_normalization` | 330 | `"observed_positive_rate":float(observed.mean()) if len(observed) else np.nan,` |
| 39 | `global_normalization` | 367 | `mae=float(test["validation_mae_pct"].mean())` |
| 39 | `global_normalization` | 368 | `rmse=float(test["validation_rmse_pct"].mean())` |
| 39 | `global_normalization` | 369 | `direction=float(test["directional_accuracy_pct"].mean())` |
| 39 | `global_normalization` | 378 | `"testing_rows":len(test),"training_end_date":pd.Timestamp(forecasts["forecast_date"].max()).date(),` |
| 39 | `global_normalization` | 379 | `"testing_start_date":pd.Timestamp(forecasts["forecast_date"].max()).date(),` |
| 39 | `global_normalization` | 380 | `"testing_end_date":pd.Timestamp(forecasts["forecast_date"].max()).date(),` |
| 39 | `global_normalization` | 392 | `sign_consistency=max((signs>=0).mean(),(signs<=0).mean())*100` |
| 39 | `global_normalization` | 393 | `top5=(group["importance_rank"]<=5).mean()*100` |
| 39 | `global_normalization` | 395 | `mean_abs=float(values.abs().mean())` |
| 39 | `global_normalization` | 514 | `direction=float((np.sign(realized)==np.sign(usable["predicted_return_pct"])).mean()*100)` |
| 39 | `global_normalization` | 518 | `coverage=float(((realized>=usable["lower_return_pct"])&(realized<=usable["upper_return_pct"])).mean()*100)` |
| 39 | `global_normalization` | 520 | `sharpe=float(strategy.mean()/strategy.std(ddof=0)*math.sqrt(365/max(int(horizon),1))) if strategy.std(ddof=0)>0 else 0.0` |
| 39 | `global_normalization` | 525 | `"mean_absolute_error_pct":float(error.abs().mean()),` |
| 39 | `global_normalization` | 530 | `"mean_interval_width_pct":float((usable["upper_return_pct"]-usable["lower_return_pct"]).mean()),` |
| 39 | `global_normalization` | 559 | `improvement=float((calibration["calibration_improvement_pct"]>0).mean()*100)` |
| 39 | `global_normalization` | 560 | `mean_brier=float(calibration["calibrated_brier_score"].mean())` |
| 39 | `global_normalization` | 561 | `coverage=float(rolling["interval_coverage_pct"].mean()) if not rolling.empty else 0.0` |
| 39 | `global_normalization` | 562 | `direction=float(rolling["directional_accuracy_pct"].mean()) if not rolling.empty else 0.0` |
| 39 | `global_normalization` | 572 | `(evidence_ready["stability_score"]>=65).mean()*100` |
| 40 | `global_normalization` | 1007 | `probability.mean()` |
| 40 | `global_normalization` | 1008 | `- outcome.mean()` |
| 40 | `global_normalization` | 1023 | `strategy_return.mean()` |
| 40 | `global_normalization` | 1051 | `].mean()` |
| 40 | `global_normalization` | 1094 | `].mean()` |
| 40 | `global_normalization` | 1109 | `].mean()` |
| 40 | `global_normalization` | 1116 | `].mean()` |
| 40 | `global_normalization` | 1122 | `].mean()` |
| 40 | `global_normalization` | 1182 | `].mean()` |
| 40 | `global_normalization` | 1187 | `].mean()` |
| 40 | `global_normalization` | 1251 | `].mean()` |
| 40 | `global_normalization` | 1259 | `].mean()` |
| 40 | `global_normalization` | 1264 | `].mean()` |
| 40 | `global_normalization` | 1291 | `].mean()` |
| 40 | `global_normalization` | 1299 | `].mean()` |
| 40 | `global_normalization` | 1360 | `].mean()` |
| 40 | `global_normalization` | 1365 | `].mean()` |
| 40 | `global_normalization` | 1370 | `].mean()` |
| 40 | `global_normalization` | 1376 | `].mean()` |
| 40 | `global_normalization` | 1382 | `].mean()` |
| 40 | `global_normalization` | 1385 | `].mean()` |
| 40 | `global_normalization` | 1525 | `].mean()` |
| 40 | `global_normalization` | 1530 | `].mean()` |
| 40 | `global_normalization` | 1547 | `].mean()` |
| 40 | `global_normalization` | 1551 | `probability.mean()` |
| 40 | `global_normalization` | 1552 | `- outcome.mean()` |
| 40 | `global_normalization` | 1627 | `memory["forecast_date"].min()` |
| 40 | `global_normalization` | 1632 | `memory["forecast_date"].max()` |
| 41 | `global_normalization` | 208 | `prior=float(mg["ensemble_weight"].mean())` |
| 41 | `global_normalization` | 214 | `realized_mae=float(matured.absolute_error_pct.mean())` |
| 41 | `global_normalization` | 253 | `realized_mae=float(matured.absolute_error_pct.mean())` |
| 41 | `global_normalization` | 254 | `direction=float(matured.direction_correct.mean()*100)` |
| 41 | `global_normalization` | 258 | `coverage=float(matured.interval_covered.mean()*100)` |
| 41 | `global_normalization` | 385 | `mean_rel=float(reliability.reliability_score.mean()) if not reliability.empty else 0` |
| 41 | `global_normalization` | 386 | `mean_change=float(confidence.confidence_change.mean()) if not confidence.empty else 0` |
| 42 | `global_normalization` | 342 | `float(returns.mean() * 365)` |
| 42 | `global_normalization` | 359 | `(price / peak - 1).min()` |
| 42 | `global_normalization` | 1611 | `prices["price_date"].max()` |
| 43 | `global_normalization` | 472 | `].max()` |
| 43 | `global_normalization` | 474 | `prior["recommendation_date"].max()` |
| 44 | `global_normalization` | 352 | `mean_realized = matured["realized_return_pct"].mean()` |
| 44 | `global_normalization` | 353 | `mean_strategy = matured["strategy_return_pct"].mean()` |
| 44 | `global_normalization` | 354 | `excess_cash = matured["excess_vs_cash_pct"].mean()` |
| 44 | `global_normalization` | 355 | `excess_hold = matured["excess_vs_buy_hold_pct"].mean()` |
| 44 | `global_normalization` | 356 | `positive = matured["economic_value_positive"].astype(float).mean() * 100` |
| 44 | `global_normalization` | 357 | `directional = matured["direction_correct"].astype(float).mean() * 100` |
| 44 | `global_normalization` | 392 | `"EQUAL_WEIGHT_CRYPTO": group.groupby("recommendation_date")["buy_hold_return_pct"].mean(),` |
| 44 | `global_normalization` | 402 | `sharpe = r.mean() / r.std(ddof=0) * math.sqrt(365 / max(int(horizon), 1)) if r.std(ddof=0) > 0 else 0.0` |
| 44 | `global_normalization` | 404 | `drawdown = (wealth / wealth.cummax() - 1).min() * 100` |
| 44 | `global_normalization` | 415 | `"positive_period_pct": (series > 0).mean() * 100,` |
| 44 | `global_normalization` | 416 | `"mean_period_return_pct": series.mean(),` |
| 44 | `global_normalization` | 430 | `sharpe = strategy.mean() / strategy.std(ddof=0) * math.sqrt(365 / int(horizon)) if strategy.std(ddof=0) > 0 else 0.0` |
| 44 | `global_normalization` | 432 | `0.40 * min(max(excess.mean() + 50, 0), 100)` |
| 44 | `global_normalization` | 433 | `+ 0.25 * group["direction_correct"].astype(float).mean() * 100` |
| 44 | `global_normalization` | 434 | `+ 0.20 * group["economic_value_positive"].astype(float).mean() * 100` |
| 44 | `global_normalization` | 441 | `"strategy_return_pct": strategy.mean(),` |
| 44 | `global_normalization` | 442 | `"buy_hold_return_pct": buy_hold.mean(),` |
| 44 | `global_normalization` | 443 | `"excess_return_pct": excess.mean(),` |
| 44 | `global_normalization` | 444 | `"directional_accuracy_pct": group["direction_correct"].astype(float).mean() * 100,` |
| 44 | `global_normalization` | 445 | `"positive_value_rate_pct": group["economic_value_positive"].astype(float).mean() * 100,` |
| 44 | `global_normalization` | 513 | `equal_weight = hold_r.mean() * 100` |
| 44 | `global_normalization` | 571 | `positive_rate = matured["economic_value_positive"].astype(float).mean() * 100` |
| 44 | `global_normalization` | 572 | `excess_cash = matured["excess_vs_cash_pct"].mean()` |
| 44 | `global_normalization` | 573 | `excess_hold = matured["excess_vs_buy_hold_pct"].mean()` |
| 44 | `global_normalization` | 577 | `strategy_return = portfolio["strategy_portfolio_return_pct"].mean() if not portfolio.empty else matured["strategy_return_pct"].mean()` |
| 44 | `global_normalization` | 578 | `benchmark_return = portfolio["equal_weight_crypto_return_pct"].mean() if not portfolio.empty else matured["buy_hold_return_pct"].mean()` |

## Interpretation

- Detected evidence means a term or implementation pattern exists.
- It does not prove correct time ordering or true out-of-sample use.
- Every critical capability requires targeted code inspection.
- Every performance claim requires reproducible historical execution.
- Potential leakage findings require manual review before certification.
