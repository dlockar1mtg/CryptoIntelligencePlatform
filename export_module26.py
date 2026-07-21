from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module26 import MODULE26_SCHEMA
EXPORTS={'latest_m26_research_summary':'SELECT * FROM latest_m26_research_summary','latest_m26_feature_research':'SELECT * FROM latest_m26_feature_research','latest_m26_nested_walk_forward':'SELECT * FROM latest_m26_nested_walk_forward','latest_m26_ensemble_optimization':'SELECT * FROM latest_m26_ensemble_optimization','latest_m26_probability_calibration':'SELECT * FROM latest_m26_probability_calibration','latest_m26_transition_matrix':'SELECT * FROM latest_m26_transition_matrix','latest_m26_sensitivity_results':'SELECT * FROM latest_m26_sensitivity_results','module26_runs':'SELECT * FROM module26_runs'}
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE26_SCHEMA); d=path_for(s,'export_directory'); d.mkdir(parents=True,exist_ok=True)
 for n,q in EXPORTS.items():
  f=c.execute(q).fetchdf(); p=d/f'{n}.csv'; f.to_csv(p,index=False); print(f'{n}: {len(f)} rows -> {p}')
 c.close()
if __name__=='__main__': main()
