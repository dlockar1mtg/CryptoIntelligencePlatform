from pathlib import Path
import shutil,yaml
ROOT=Path(__file__).resolve().parent; P=ROOT/'config'/'settings.yaml'
CONFIG={'feature_selection':{'minimum_coverage':0.70,'minimum_features':6,'maximum_features':10,'maximum_pairwise_correlation':0.88},'models':{'random_state':710},'nested_walk_forward':{'minimum_training_days':540,'outer_test_days':90,'inner_validation_days':120},'ensemble_search':{'gmm_weights':[0.25,0.35,0.45],'kmeans_weights':[0.10,0.20],'rule_weights':[0.20,0.30,0.40],'markov_weights':[0.10,0.20,0.30],'smoothing_values':[0.55,0.70,0.82]},'validation':{'minimum_nested_agreement_pct':55,'maximum_calibrated_mae':0.18,'minimum_sensitivity_stability_pct':70}}
def main():
 if not P.exists(): raise FileNotFoundError(f'Missing settings: {P}')
 b=P.with_name('settings_before_v7_1.yaml')
 if not b.exists(): shutil.copy2(P,b); print(f'Settings backup: {b}')
 s=yaml.safe_load(P.read_text(encoding='utf-8')); s['module26']=CONFIG
 if 'platform' in s: s['platform']['version']='7.1.0'
 P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding='utf-8'); print('v7.1 configuration applied.')
if __name__=='__main__': main()
