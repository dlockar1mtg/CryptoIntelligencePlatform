from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module16 import MODULE16_SCHEMA
EXPORTS={
 'latest_candidate_rankings':'SELECT * FROM latest_candidate_rankings',
 'candidate_rankings':'SELECT * FROM candidate_rankings',
 'latest_strategy_candidates':'SELECT * FROM latest_strategy_candidates',
 'strategy_candidates':'SELECT * FROM strategy_candidates',
 'candidate_results':'SELECT * FROM candidate_results',
 'candidate_evaluation_cache':'SELECT * FROM candidate_evaluation_cache',
 'latest_parameter_importance':'SELECT * FROM latest_parameter_importance',
 'parameter_importance':'SELECT * FROM parameter_importance',
 'optimization_runs':'SELECT * FROM optimization_runs',
 'optimization_history':'SELECT * FROM optimization_history'}
def main():
 s,_=load_all();c=connect(s);c.execute(MODULE16_SCHEMA);d=path_for(s,'export_directory');d.mkdir(parents=True,exist_ok=True)
 for n,q in EXPORTS.items():
  f=c.execute(q).fetchdf();o=d/f'{n}.csv';f.to_csv(o,index=False);print(f'{n}: {len(f)} rows -> {o}')
 c.close()
if __name__=='__main__':main()
