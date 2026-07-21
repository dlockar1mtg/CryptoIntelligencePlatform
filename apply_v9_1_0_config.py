from pathlib import Path
import shutil,yaml
P=Path(__file__).resolve().parent/'config'/'settings.yaml'
def main():
 b=P.with_name('settings_before_v9_1_0.yaml');
 if not b.exists(): shutil.copy2(P,b); print(f'Settings backup: {b}')
 s=yaml.safe_load(P.read_text(encoding='utf-8')); s['module35']={'lookback_days':180,'max_asset_weight':0.45,'target_volatility_pct':12.0}; s['module36']={'lookback_days':365,'target_volatility_pct':10.0};
 if 'platform' in s: s['platform']['version']='9.1.0'
 P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding='utf-8'); print('v9.1.0 configuration applied.')
if __name__=='__main__': main()
