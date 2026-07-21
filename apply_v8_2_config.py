from pathlib import Path
import shutil,yaml
ROOT=Path(__file__).resolve().parent; P=ROOT/'config'/'settings.yaml'
CONFIG={
'persistence':{'smoothing_values':[0.0,0.25,0.50,0.70],'transition_strength_values':[0.0,0.5,1.0,1.5]},
'forward_returns':{'horizons_days':[30,60,90]},
'validation':{'minimum_accuracy_pct':55,'maximum_log_loss':1.75}}
def main():
 if not P.exists(): raise FileNotFoundError(f'Missing settings: {P}')
 b=P.with_name('settings_before_v8_2.yaml')
 if not b.exists(): shutil.copy2(P,b); print(f'Settings backup: {b}')
 s=yaml.safe_load(P.read_text(encoding='utf-8')); s['module31']=CONFIG
 if 'platform' in s: s['platform']['version']='8.2.0'
 P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding='utf-8'); print('v8.2 configuration applied.')
if __name__=='__main__': main()
