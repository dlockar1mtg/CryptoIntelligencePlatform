from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module17 import MODULE17_SCHEMA

EXPORTS = {
    "crypto_features_daily": "SELECT * FROM crypto_features_daily",
    "latest_feature_validation": "SELECT * FROM latest_feature_validation",
    "feature_validation_results": "SELECT * FROM feature_validation_results",
    "latest_feature_readiness": "SELECT * FROM latest_feature_readiness",
    "feature_readiness": "SELECT * FROM feature_readiness",
    "external_feature_observations": "SELECT * FROM external_feature_observations",
    "module17_runs": "SELECT * FROM module17_runs",
}

def main():
    s, _ = load_all()
    c = connect(s)
    c.execute(MODULE17_SCHEMA)
    d = path_for(s, "export_directory")
    d.mkdir(parents=True, exist_ok=True)
    for name, sql in EXPORTS.items():
        f = c.execute(sql).fetchdf()
        out = d / f"{name}.csv"
        f.to_csv(out, index=False)
        print(f"{name}: {len(f)} rows -> {out}")
    c.close()

if __name__ == "__main__":
    main()
