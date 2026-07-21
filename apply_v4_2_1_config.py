from pathlib import Path
import shutil,yaml
ROOT=Path(__file__).resolve().parent
SETTINGS=ROOT/'config'/'settings.yaml'
CONFIG={'collection':{'enabled':True,'url':'https://stablecoins.llama.fi/stablecoincharts/all','timeout_seconds':45},'horizons_days':[30,90,180],'interactions':{'maximum_features':10,'maximum_pairs':45,'minimum_observations':180},'permutation':{'enabled':True,'n_estimators':300,'n_repeats':10,'random_state':4201,'minimum_observations':365},'regimes':{'sma_days':200,'momentum_days':90,'minimum_observations':45},'readiness':{'minimum_history_days':180,'minimum_active_window_coverage_pct':80,'minimum_absolute_spearman':0.05}}
def main():
    if not SETTINGS.exists(): raise FileNotFoundError(f'Missing settings file: {SETTINGS}')
    backup=SETTINGS.with_name('settings_before_v4_2_1.yaml')
    if not backup.exists(): shutil.copy2(SETTINGS,backup); print(f'Settings backup: {backup}')
    settings=yaml.safe_load(SETTINGS.read_text(encoding='utf-8'))
    settings['module18']=CONFIG
    if 'platform' in settings: settings['platform']['version']='4.2.1'
    SETTINGS.write_text(yaml.safe_dump(settings,sort_keys=False,allow_unicode=True),encoding='utf-8')
    print('v4.2.1 configuration applied.')
if __name__=='__main__': main()
