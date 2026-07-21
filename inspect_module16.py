from crypto_platform.platform import load_all,connect
from crypto_platform.module16 import MODULE16_SCHEMA

def show(c,title,sql):
 print(f"\n{title}\n"+'-'*len(title)); f=c.execute(sql).fetchdf(); print(f.to_string(index=False) if not f.empty else 'No data.')
def main():
 s,_=load_all();c=connect(s);c.execute(MODULE16_SCHEMA)
 show(c,'TOP OPTIMIZED CANDIDATES',"SELECT candidate_id,full_sample_rank,full_sample_objective,oos_folds,oos_total_return_pct,oos_btc_return_pct,oos_btc_excess_pct,oos_information_ratio,oos_maximum_drawdown_pct,oos_benchmark_win_rate_pct,stability_score,robust_score,promotion_status FROM latest_candidate_rankings LIMIT 25")
 show(c,'BEST CANDIDATE PARAMETERS',"SELECT c.candidate_id,c.parameters_json FROM latest_strategy_candidates c JOIN latest_candidate_rankings r USING(candidate_id) ORDER BY r.robust_score DESC LIMIT 10")
 show(c,'PARAMETER IMPORTANCE',"SELECT parameter_name,correlation_to_objective,top_quartile_mean,bottom_quartile_mean,importance_score FROM latest_parameter_importance")
 show(c,'OPTIMIZATION RUNS',"SELECT started_at_utc,completed_at_utc,status,candidate_count,evaluated_count,cached_count,shortlist_count,walk_forward_count,best_candidate_id,best_robust_score,notes FROM optimization_runs ORDER BY started_at_utc DESC LIMIT 10")
 c.close()
if __name__=='__main__':main()
