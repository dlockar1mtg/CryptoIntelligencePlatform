from pathlib import Path
import shutil,yaml
ROOT=Path(__file__).resolve().parent; P=ROOT/'config'/'settings.yaml'
CONFIG={
'horizons_days':[30,90,180],
'models':{'training_fraction':0.75,'minimum_total_rows':365,'minimum_training_rows':240,'minimum_testing_rows':60,'n_estimators':250,'gradient_estimators':200,'hist_iterations':250,'learning_rate':0.04,'max_depth':3,'max_leaf_nodes':15,'min_samples_leaf':15,'l2_regularization':1.0,'random_state':423},
'explainability':{'n_repeats':8},
'redundancy':{'absolute_correlation_threshold':0.85,'minimum_observations':180},
'aging':{'recent_windows':6,'full_decay_days':120,'target_recent_absolute_spearman':0.20,'minimum_recent_sign_consistency_pct':55,'shadow_minimum_score':60,'watchlist_minimum_score':40},
'shadow':{'zscore_lookback_days':365,'minimum_feature_history':120,'neutral_btc_weight':0.70,'signal_weight_slope':0.12,'minimum_btc_weight':0.20,'maximum_btc_weight':1.00,'transaction_cost_bps':15,'fallback_minimum_aged_score':55,'minimum_excess_return_pct':0,'minimum_information_ratio':0,'maximum_drawdown_floor_pct':-65}}
def main():
    if not P.exists():raise FileNotFoundError(P)
    b=P.with_name('settings_before_v4_2_3.yaml')
    if not b.exists():shutil.copy2(P,b);print(f'Settings backup: {b}')
    s=yaml.safe_load(P.read_text(encoding='utf-8'));s['module20']=CONFIG
    if 'platform' in s:s['platform']['version']='4.2.3'
    P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding='utf-8');print('v4.2.3 configuration applied.')
if __name__=='__main__':main()
