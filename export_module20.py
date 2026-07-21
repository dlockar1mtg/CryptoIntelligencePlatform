from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module20 import MODULE20_SCHEMA
EXPORTS={'latest_feature_model_comparison':'SELECT * FROM latest_feature_model_comparison','feature_model_comparison':'SELECT * FROM feature_model_comparison','latest_model_feature_explainability':'SELECT * FROM latest_model_feature_explainability','model_feature_explainability':'SELECT * FROM model_feature_explainability','latest_feature_redundancy':'SELECT * FROM latest_feature_redundancy','feature_redundancy_analysis':'SELECT * FROM feature_redundancy_analysis','latest_feature_evidence_aging':'SELECT * FROM latest_feature_evidence_aging','feature_evidence_aging':'SELECT * FROM feature_evidence_aging','latest_shadow_portfolio_periods':'SELECT * FROM latest_shadow_portfolio_periods','shadow_portfolio_periods':'SELECT * FROM shadow_portfolio_periods','latest_shadow_portfolio_summary':'SELECT * FROM latest_shadow_portfolio_summary','shadow_portfolio_summary':'SELECT * FROM shadow_portfolio_summary','module20_runs':'SELECT * FROM module20_runs'}
def main():
    s,_=load_all();c=connect(s);c.execute(MODULE20_SCHEMA);d=path_for(s,'export_directory');d.mkdir(parents=True,exist_ok=True)
    for n,q in EXPORTS.items():
        f=c.execute(q).fetchdf();o=d/f'{n}.csv';f.to_csv(o,index=False);print(f'{n}: {len(f)} rows -> {o}')
    c.close()
if __name__=='__main__':main()
