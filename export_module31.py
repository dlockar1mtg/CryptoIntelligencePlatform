from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module31 import MODULE31_SCHEMA
EXPORTS={
'latest_m31_research_summary':'SELECT * FROM latest_m31_research_summary',
'latest_m31_calibration_comparison':'SELECT * FROM latest_m31_calibration_comparison',
'latest_m31_persistence_validation':'SELECT * FROM latest_m31_persistence_validation',
'latest_m31_forward_return_validation':'SELECT * FROM latest_m31_forward_return_validation',
'latest_m31_regime_economic_scorecard':'SELECT * FROM latest_m31_regime_economic_scorecard',
'latest_m31_global_feature_validation':'SELECT * FROM latest_m31_global_feature_validation',
'latest_m31_disagreement_outcomes':'SELECT * FROM latest_m31_disagreement_outcomes',
'module31_runs':'SELECT * FROM module31_runs'}
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE31_SCHEMA); d=path_for(s,'export_directory'); d.mkdir(parents=True,exist_ok=True)
 for n,q in EXPORTS.items():
  f=c.execute(q).fetchdf(); p=d/f'{n}.csv'; f.to_csv(p,index=False); print(f'{n}: {len(f)} rows -> {p}')
 c.close()
if __name__=='__main__': main()
