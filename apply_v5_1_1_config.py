from pathlib import Path
import shutil,yaml
R=Path(__file__).resolve().parent; P=R/'config'/'settings.yaml'
C={'audit':{'return_error_tolerance_pct':0.0001,'expected_rebalance_days':30},'labels':{'minimum_acceptable_auc':0.55,'minimum_inverted_auc':0.60},'bootstrap':{'simulations':10000,'seed':511},'promotion':{'minimum_probability_excess_positive':0.95,'minimum_corrected_excess_pct':0,'minimum_information_ratio':0}}
def main():
 if not P.exists(): raise FileNotFoundError(f'Missing settings: {P}')
 b=P.with_name('settings_before_v5_1_1.yaml')
 if not b.exists(): shutil.copy2(P,b); print(f'Settings backup: {b}')
 s=yaml.safe_load(P.read_text(encoding='utf-8')); s['module23']=C
 if 'platform' in s:s['platform']['version']='5.1.1'
 P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding='utf-8'); print('v5.1.1 configuration applied.')
if __name__=='__main__':main()
