from crypto_platform.platform import load_all,connect
from crypto_platform.module18 import MODULE18_SCHEMA

def show(c,t,q):
    print(f'\n{t}\n'+('-'*len(t)))
    f=c.execute(q).fetchdf()
    print(f.to_string(index=False) if not f.empty else 'No data.')

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE18_SCHEMA)
    show(c,'CORRECTED FEATURE READINESS',"SELECT feature_key,first_date,latest_date,active_window_days,non_null_count,active_window_coverage_pct,full_table_coverage_pct,best_absolute_spearman,readiness_status,limitation FROM latest_feature_readiness_v2")
    show(c,'TOP FEATURE INTERACTIONS',"SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_feature_interactions LIMIT 30")
    show(c,'PERMUTATION IMPORTANCE',"SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_feature_permutation_importance")
    show(c,'REGIME STABILITY',"SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_feature_regime_stability ORDER BY ABS(spearman_correlation) DESC LIMIT 40")
    show(c,'LATEST MODULE 18 RUNS',"SELECT started_at_utc,completed_at_utc,status,stablecoin_history_rows,corrected_readiness_rows,interaction_rows,permutation_rows,regime_rows,notes FROM module18_runs ORDER BY started_at_utc DESC LIMIT 10")
    c.close()
if __name__=='__main__': main()
