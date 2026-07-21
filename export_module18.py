from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module18 import MODULE18_SCHEMA
EXPORTS={'latest_feature_readiness_v2':'SELECT * FROM latest_feature_readiness_v2','feature_readiness_v2':'SELECT * FROM feature_readiness_v2','latest_feature_interactions':'SELECT * FROM latest_feature_interactions','feature_interaction_validation':'SELECT * FROM feature_interaction_validation','latest_feature_permutation_importance':'SELECT * FROM latest_feature_permutation_importance','feature_permutation_importance':'SELECT * FROM feature_permutation_importance','latest_feature_regime_stability':'SELECT * FROM latest_feature_regime_stability','feature_regime_stability':'SELECT * FROM feature_regime_stability','module18_runs':'SELECT * FROM module18_runs'}
def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE18_SCHEMA); d=path_for(s,'export_directory'); d.mkdir(parents=True,exist_ok=True)
    for n,q in EXPORTS.items():
        f=c.execute(q).fetchdf(); o=d/f'{n}.csv'; f.to_csv(o,index=False); print(f'{n}: {len(f)} rows -> {o}')
    c.close()
if __name__=='__main__': main()
