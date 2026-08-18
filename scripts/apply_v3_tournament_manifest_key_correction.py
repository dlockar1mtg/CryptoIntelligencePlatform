from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_v3_per_horizon_development_tournament.py"
OLD = 'set(g["v3_holdout_origin_dates"])'
NEW = 'set(g["v3_final_holdout_origin_dates"])'

text = TARGET.read_text(encoding="utf-8")
count_old = text.count(OLD)
count_new = text.count(NEW)
if count_old != 1:
    raise RuntimeError(f"Expected exactly one old V3 manifest-key reference, found {count_old}")
if count_new != 0:
    raise RuntimeError(f"Corrected V3 manifest-key reference already present {count_new} time(s)")
updated = text.replace(OLD, NEW, 1)
TARGET.write_text(updated, encoding="utf-8", newline="\n")
print("CRYPTO_V3_TOURNAMENT_MANIFEST_KEY_CORRECTION=APPLIED")
print("OLD_KEY_REFERENCES_AFTER=0")
print("NEW_KEY_REFERENCES_AFTER=1")
