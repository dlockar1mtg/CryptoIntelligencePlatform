from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    target = root / "scripts" / "audit_native_point_in_time_semantics.py"
    text = target.read_text(encoding="utf-8")

    replacements = {
        'SELECT outcome_status, COUNT(*) rows FROM m44_decision_outcomes GROUP BY 1 ORDER BY 1':
            'SELECT outcome_status, COUNT(*) AS row_count FROM m44_decision_outcomes GROUP BY 1 ORDER BY 1',
        'COUNT(*) rows,\n                       COUNT(DISTINCT training_end_date) training_end_dates,':
            'COUNT(*) AS row_count,\n                       COUNT(DISTINCT training_end_date) AS training_end_dates,',
        'COUNT(DISTINCT testing_start_date) testing_start_dates,':
            'COUNT(DISTINCT testing_start_date) AS testing_start_dates,',
        'COUNT(DISTINCT testing_end_date) testing_end_dates,':
            'COUNT(DISTINCT testing_end_date) AS testing_end_dates,',
    }

    original = text
    for old, new in replacements.items():
        if old not in text:
            raise RuntimeError(f"Expected audit fragment not found: {old}")
        text = text.replace(old, new, 1)

    if text == original:
        raise RuntimeError("No audit correction was applied")

    target.write_text(text, encoding="utf-8", newline="")

    print("CRYPTO_POINT_IN_TIME_AUDIT_DUCKDB_ALIAS_CORRECTION=PASS")
    print("CORRECTION_SCOPE=SQL_ALIAS_SYNTAX_ONLY")
    print(f"UPDATED_FILE={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
