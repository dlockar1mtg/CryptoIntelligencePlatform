from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module24 import MODULE24_SCHEMA

EXPORTS = {
    'alpha_factor_daily': 'SELECT * FROM alpha_factor_daily',
    'latest_alpha_candidate_registry': 'SELECT * FROM latest_alpha_candidate_registry',
    'latest_alpha_walk_forward_results': 'SELECT * FROM latest_alpha_walk_forward_results',
    'latest_alpha_portfolio_periods': 'SELECT * FROM latest_alpha_portfolio_periods',
    'latest_alpha_label_validation': 'SELECT * FROM latest_alpha_label_validation',
    'latest_alpha_bootstrap_validation': 'SELECT * FROM latest_alpha_bootstrap_validation',
    'latest_alpha_research_summary': 'SELECT * FROM latest_alpha_research_summary',
    'module24_runs': 'SELECT * FROM module24_runs',
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE24_SCHEMA)
    directory = path_for(settings, 'export_directory')
    directory.mkdir(parents=True, exist_ok=True)
    for name, sql in EXPORTS.items():
        frame = conn.execute(sql).fetchdf()
        output = directory / f'{name}.csv'
        frame.to_csv(output, index=False)
        print(f'{name}: {len(frame)} rows -> {output}')
    conn.close()


if __name__ == '__main__':
    main()
