from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "crypto_platform" / "module38.py"

OLD_FEATURE_RETURN = '''        features["target_return"] = (\n            price.shift(-horizon) / price - 1\n        )\n        return features.replace(\n            [np.inf, -np.inf],\n            np.nan,\n        ).dropna()\n'''

NEW_FEATURE_RETURN = '''        features["target_return"] = (\n            price.shift(-horizon) / price - 1\n        )\n        features = features.replace(\n            [np.inf, -np.inf],\n            np.nan,\n        )\n\n        # Keep the point-in-time price-derived feature set authoritative.\n        # Market-cap and volume history are optional provider features with\n        # materially shorter coverage than canonical price history. Do not\n        # discard otherwise valid long-horizon training origins merely because\n        # an optional provider feature is unavailable. Missing optional features\n        # remain missing; if an optional feature is not complete for the\n        # eligible historical frame, exclude that feature from this fit rather\n        # than synthesizing a value.\n        required_columns = [\n            "observation_date",\n            "return_1d",\n            "return_7d",\n            "return_30d",\n            "return_90d",\n            "volatility_30d",\n            "volatility_90d",\n            "distance_sma50",\n            "distance_sma200",\n            "target_return",\n        ]\n        usable = features.dropna(subset=required_columns).copy()\n        optional_columns = [\n            "volume_change_30d",\n            "market_cap_change_30d",\n        ]\n        for optional_column in optional_columns:\n            if (\n                optional_column in usable.columns\n                and usable[optional_column].isna().any()\n            ):\n                usable = usable.drop(columns=[optional_column])\n        return usable\n'''

OLD_SCALER = '''        scaler = StandardScaler()\n        x_train = scaler.fit_transform(\n            train[columns]\n        )\n        x_validation = scaler.transform(\n            validation[columns]\n        )\n        x_current = scaler.transform(\n            current_features[columns]\n        )\n'''

NEW_SCALER = '''        # Bound validation/live extrapolation to the feature support observed\n        # in the training window. This is fit-time-only information and therefore\n        # does not introduce lookahead. It prevents provider-ratio pathologies\n        # (for example a percentage change divided by a near-zero prior value)\n        # from generating unbounded standardized inputs and explosive linear\n        # predictions. Training values themselves are not clipped.\n        x_train_frame = train[columns].astype(float).copy()\n        x_validation_frame = validation[columns].astype(float).copy()\n        x_current_frame = current_features[columns].astype(float).copy()\n        training_min = x_train_frame.min(axis=0)\n        training_max = x_train_frame.max(axis=0)\n        x_validation_frame = x_validation_frame.clip(\n            lower=training_min,\n            upper=training_max,\n            axis=1,\n        )\n        x_current_frame = x_current_frame.clip(\n            lower=training_min,\n            upper=training_max,\n            axis=1,\n        )\n\n        scaler = StandardScaler()\n        x_train = scaler.fit_transform(x_train_frame)\n        x_validation = scaler.transform(x_validation_frame)\n        x_current = scaler.transform(x_current_frame)\n'''


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label} block; found {count}. "
            "Refusing non-deterministic edit."
        )
    return source.replace(old, new, 1)


def main() -> int:
    source = TARGET.read_text(encoding="utf-8-sig")
    source = replace_once(
        source,
        OLD_FEATURE_RETURN,
        NEW_FEATURE_RETURN,
        "Module 38 feature-frame finalization",
    )
    source = replace_once(
        source,
        OLD_SCALER,
        NEW_SCALER,
        "Module 38 scaler",
    )
    TARGET.write_text(source, encoding="utf-8", newline="")

    updated = TARGET.read_text(encoding="utf-8")
    required_tokens = (
        "usable = features.dropna(subset=required_columns).copy()",
        "optional_columns = [",
        "usable = usable.drop(columns=[optional_column])",
        "training_min = x_train_frame.min(axis=0)",
        "training_max = x_train_frame.max(axis=0)",
        "x_validation_frame = x_validation_frame.clip(",
        "x_current_frame = x_current_frame.clip(",
        "x_train = scaler.fit_transform(x_train_frame)",
    )
    missing = [token for token in required_tokens if token not in updated]
    if missing:
        raise RuntimeError(
            "Module 38 feature stability remediation is incomplete: "
            + ", ".join(missing)
        )

    print("CRYPTO_MODULE38_FEATURE_STABILITY_REMEDIATION=PASS")
    print("OPTIONAL_PROVIDER_FEATURES_SYNTHESIZED=FALSE")
    print("INCOMPLETE_OPTIONAL_PROVIDER_FEATURES_EXCLUDED=TRUE")
    print("VALIDATION_AND_LIVE_FEATURES_BOUNDED_BY_TRAINING_SUPPORT=TRUE")
    print("TRAINING_FEATURES_CLIPPED=FALSE")
    print(f"UPDATED_FILE={TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
