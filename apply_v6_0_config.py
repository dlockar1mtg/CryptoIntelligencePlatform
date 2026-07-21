from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / 'config' / 'settings.yaml'
CONFIG = {
    'candidate_search': {
        'candidate_count': 180,
        'shortlist_count': 5,
        'random_seed': 600,
    },
    'portfolio': {
        'rebalance_days': 30,
        'transaction_cost_bps': 15,
    },
    'walk_forward': {
        'training_months': 24,
        'testing_months': 6,
        'step_months': 6,
    },
    'bootstrap': {
        'simulations': 10000,
        'seed': 600,
    },
    'promotion': {
        'maximum_reconciliation_error_pct': 0.0001,
        'maximum_weak_label_horizons': 1,
        'minimum_excess_return_pct': 0,
        'minimum_information_ratio': 0,
        'minimum_bootstrap_probability': 0.95,
    },
}


def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(f'Missing settings: {SETTINGS}')
    backup = SETTINGS.with_name('settings_before_v6_0.yaml')
    if not backup.exists():
        shutil.copy2(SETTINGS, backup)
        print(f'Settings backup: {backup}')
    settings = yaml.safe_load(SETTINGS.read_text(encoding='utf-8'))
    settings['module24'] = CONFIG
    settings.setdefault('platform', {})['version'] = '6.0.0'
    SETTINGS.write_text(
        yaml.safe_dump(settings, sort_keys=False, allow_unicode=True),
        encoding='utf-8',
    )
    print('v6.0 configuration applied.')


if __name__ == '__main__':
    main()
