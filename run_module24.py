from crypto_platform.module24 import run_module24


def main():
    print('Crypto Intelligence Platform — Module 24 v24.0')
    print('Quantitative research, frozen walk-forward alpha, and audit validation\n')
    result = run_module24()
    print('Module 24 summary')
    print('-----------------')
    labels = [
        ('Status', 'status'),
        ('Factor rows', 'factor_rows'),
        ('Candidates tested', 'candidates_tested'),
        ('Walk-forward folds', 'walk_forward_folds'),
        ('Selected candidate', 'selected_candidate'),
        ('Corrected return %', 'corrected_return_pct'),
        ('Bitcoin return %', 'btc_return_pct'),
        ('Excess return %', 'excess_return_pct'),
        ('Information ratio', 'information_ratio'),
        ('Bootstrap P(excess > 0)', 'bootstrap_probability_positive'),
        ('Audit status', 'audit_status'),
        ('Promotion status', 'promotion_status'),
        ('Run ID', 'run_id'),
    ]
    for label, key in labels:
        print(f'{label + ":":30} {result[key]}')


if __name__ == '__main__':
    main()
