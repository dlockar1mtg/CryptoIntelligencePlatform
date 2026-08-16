from __future__ import annotations

from pathlib import Path


def main() -> int:
    target = Path(__file__).with_name("diagnose_module39_stability_and_drift_semantics.py")
    source = target.read_text(encoding="utf-8")
    old = (
        "SELECT run_id, validation_status, recommendation,\n"
        "                       stable_feature_pct, current_drift_status,\n"
        "                       mean_directional_accuracy_pct, mean_calibrated_brier\n"
        "                FROM m39_validation_summary s\n"
        "                JOIN module39_runs r USING(run_id)"
    )
    new = (
        "SELECT s.run_id, s.validation_status, r.recommendation,\n"
        "                       s.stable_feature_pct, s.current_drift_status,\n"
        "                       s.mean_directional_accuracy_pct, s.mean_calibrated_brier\n"
        "                FROM m39_validation_summary s\n"
        "                JOIN module39_runs r USING(run_id)"
    )
    if old not in source:
        raise RuntimeError("Expected ambiguous Module 39 summary query was not found.")
    corrected = source.replace(old, new, 1)
    namespace = {
        "__name__": "__main__",
        "__file__": str(target),
        "__package__": None,
    }
    exec(compile(corrected, str(target), "exec"), namespace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
