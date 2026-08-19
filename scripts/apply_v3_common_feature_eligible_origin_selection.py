from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "run_v3_per_horizon_development_tournament.py"

OLD = '''                    safe_indices = []
                    for candidate_pos in candidates:
                        original_idx = int(candidate_frame.iloc[candidate_pos]["_original_index"])
                        date_key = pd.Timestamp(features.iloc[original_idx]["observation_date"]).date().isoformat()
                        if date_key in v2_dates[key] or date_key in v3_dates[key]:
                            continue
                        safe_indices.append(original_idx)
                    required = DEVELOPMENT_FOLDS * ORIGINS_PER_FOLD
'''

NEW = '''                    safe_indices = []
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
'''

text = HARNESS.read_text(encoding="utf-8")
if text.count(OLD) != 1:
    raise RuntimeError(f"Expected exactly one governed safe-index selection block, found {text.count(OLD)}")
if "selection_columns = sorted({" in text:
    raise RuntimeError("Common feature-eligible origin selection already appears to be applied")
HARNESS.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="\n")
print("CRYPTO_V3_COMMON_FEATURE_ELIGIBLE_ORIGIN_SELECTION=APPLIED")
print("COMMON_ORIGIN_SELECTION_ENFORCED=TRUE")
print("MISSING_FEATURES_SYNTHESIZED=FALSE")
