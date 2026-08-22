from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "run_v3_per_horizon_development_tournament.py"

OLD_SOURCE_LINE = '        source["observation_date"] = pd.to_datetime(source["observation_date"])\n'
NEW_SOURCE_LINE = '        source["observation_date"] = pd.to_datetime(source["observation_date"]).astype("datetime64[ns]")\n'
OLD_BASE_LINE = '    base_dates = pd.to_datetime(out["observation_date"])\n'
NEW_BASE_LINE = '    base_dates = pd.to_datetime(out["observation_date"]).astype("datetime64[ns]")\n'

text = HARNESS.read_text(encoding="utf-8")

if text.count(OLD_SOURCE_LINE) != 1:
    raise RuntimeError(f"Expected exactly one source datetime normalization line, found {text.count(OLD_SOURCE_LINE)}")
if text.count(OLD_BASE_LINE) != 1:
    raise RuntimeError(f"Expected exactly one base datetime normalization line, found {text.count(OLD_BASE_LINE)}")
if NEW_SOURCE_LINE in text or NEW_BASE_LINE in text:
    raise RuntimeError("Datetime-unit correction appears to have already been applied")

updated = text.replace(OLD_BASE_LINE, NEW_BASE_LINE, 1).replace(OLD_SOURCE_LINE, NEW_SOURCE_LINE, 1)
HARNESS.write_text(updated, encoding="utf-8", newline="")

print("CRYPTO_V3_TOURNAMENT_DATETIME_UNIT_CORRECTION=APPLIED")
print("BASE_DATES_NORMALIZED_TO_NS=TRUE")
print("SOURCE_DATES_NORMALIZED_TO_NS=TRUE")
print("TOURNAMENT_SEMANTICS_CHANGED=FALSE")
