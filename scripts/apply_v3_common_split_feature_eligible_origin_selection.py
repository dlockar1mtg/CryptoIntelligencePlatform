from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_v3_per_horizon_development_tournament.py"

OLD = '''                    candidate_frame = features.dropna(subset=["target_return"]).reset_index(drop=False).rename(columns={"index": "_original_index"})
                    safe_indices = []
                    selection_columns = sorted({
                        column
                        for family in contract["families"]
                        for column in family_columns(family, contract)
                    })
                    for candidate_pos in candidates:
                        original_idx = int(candidate_frame.iloc[candidate_pos]["_original_index"])
                        date_key = pd.Timestamp(features.iloc[original_idx]["observation_date"]).date().isoformat()
                        if date_key in v2_dates[key] or date_key in v3_dates[key]:
                            continue
                        current_probe = features.iloc[[original_idx]].copy()
                        current_probe = attach_lagged_native(current_probe, context, contract["native"])
                        current_probe = attach_relative(current_probe, relative, asset, contract["relative"])
                        if current_probe[selection_columns].isna().any(axis=1).iloc[0]:
                            continue
                        safe_indices.append(original_idx)
                    required = DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD
                    require(len(safe_indices) >= required, f"Insufficient development origins for {asset} {horizon}d")
                    positions = np.linspace(0, len(safe_indices) - 1, required, dtype=int)
                    selected = [safe_indices[int(pos)] for pos in positions]
                    excluded = set(v2_dates[key]) | set(v3_dates[key])
'''

NEW = '''                    candidate_frame = features.dropna(subset=["target_return"]).reset_index(drop=False).rename(columns={"index": "_original_index"})
                    safe_indices = []
                    excluded = set(v2_dates[key]) | set(v3_dates[key])
                    selection_columns = sorted({
                        column
                        for family in contract["families"]
                        for column in family_columns(family, contract)
                    })
                    minimum_training_rows = int(runner.cfg.get("absolute_minimum_training_rows", 90))
                    minimum_validation_rows = int(runner.cfg.get("minimum_validation_rows", 30))
                    for candidate_pos in candidates:
                        original_idx = int(candidate_frame.iloc[candidate_pos]["_original_index"])
                        date_key = pd.Timestamp(features.iloc[original_idx]["observation_date"]).date().isoformat()
                        if date_key in excluded:
                            continue
                        try:
                            _, train_probe, validation_probe, current_probe = split_origin(
                                features, original_idx, horizon, runner, excluded
                            )
                        except RuntimeError:
                            continue
                        train_probe = attach_lagged_native(train_probe, context, contract["native"])
                        validation_probe = attach_lagged_native(validation_probe, context, contract["native"])
                        current_probe = attach_lagged_native(current_probe, context, contract["native"])
                        train_probe = attach_relative(train_probe, relative, asset, contract["relative"])
                        validation_probe = attach_relative(validation_probe, relative, asset, contract["relative"])
                        current_probe = attach_relative(current_probe, relative, asset, contract["relative"])
                        if current_probe[selection_columns].isna().any(axis=1).iloc[0]:
                            continue
                        if len(train_probe.dropna(subset=selection_columns + ["target_return"])) < minimum_training_rows:
                            continue
                        if len(validation_probe.dropna(subset=selection_columns + ["target_return"])) < minimum_validation_rows:
                            continue
                        safe_indices.append(original_idx)
                    required = DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD
                    require(len(safe_indices) >= required, f"Insufficient common split-feature-complete development origins for {asset} {horizon}d")
                    positions = np.linspace(0, len(safe_indices) - 1, required, dtype=int)
                    selected = [safe_indices[int(pos)] for pos in positions]
'''

text = TARGET.read_text(encoding="utf-8")
if text.count(OLD) != 1:
    raise RuntimeError(f"Expected exactly one governed selection block, found {text.count(OLD)}")
if "common split-feature-complete development origins" in text:
    raise RuntimeError("Common split-feature eligibility correction already appears to be applied")

TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="\n")
print("CRYPTO_V3_COMMON_SPLIT_FEATURE_ELIGIBLE_ORIGIN_SELECTION=APPLIED")
print("COMMON_SPLIT_FEATURE_SELECTION_ENFORCED=TRUE")
print("MISSING_FEATURES_SYNTHESIZED=FALSE")
print("V3_HOLDOUT_OUTCOMES_VIEWED=FALSE")
