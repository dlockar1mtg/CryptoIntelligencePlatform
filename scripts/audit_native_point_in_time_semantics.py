from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def contains(source: str, *parts: str) -> bool:
    return all(part in source for part in parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    require(args.source_commit == EXPECTED_SOURCE_COMMIT, "Unexpected certified source commit")

    root = Path(__file__).resolve().parents[1]
    db = Path(args.database).resolve()
    require(db.is_file(), f"Database not found: {db}")

    db_before = sha256(db)
    module6 = (root / "crypto_platform" / "module6.py").read_text(encoding="utf-8-sig")
    module38 = (root / "crypto_platform" / "module38.py").read_text(encoding="utf-8-sig")
    module39 = (root / "crypto_platform" / "module39.py").read_text(encoding="utf-8-sig")
    module44 = (root / "crypto_platform" / "module44.py").read_text(encoding="utf-8-sig")

    findings = []

    module6_snapshot_point_in_time = contains(
        module6,
        'hist = series.loc[:date]',
        'historical_signal": self.classify_signal(overall)',
    )
    module6_forward_outcome_separated = contains(
        module6,
        'target = snapshot["observation_date"] + pd.Timedelta(days=horizon)',
        'future_price = float(candidates.iloc[0])',
        'signal_forward_performance',
    )

    if module6_snapshot_point_in_time and module6_forward_outcome_separated:
        findings.append({
            "area": "module6_historical_signal_validation",
            "status": "POINT_IN_TIME_STRUCTURE_SUPPORTED",
            "severity": "INFO",
            "finding": "Historical signal features are computed from price history truncated at each signal date; future prices are joined later for outcome evaluation.",
        })
    else:
        findings.append({
            "area": "module6_historical_signal_validation",
            "status": "REVIEW_REQUIRED",
            "severity": "HIGH",
            "finding": "Expected point-in-time separation patterns were not found.",
        })

    module38_forward_target = contains(
        module38,
        'features["target_return"] = (',
        'price.shift(-horizon) / price - 1',
    )
    module38_contiguous_split = contains(
        module38,
        'train = features.iloc[',
        ':usable_rows - validation_rows',
        'validation = features.iloc[',
        'usable_rows - validation_rows:',
    )
    module38_purge_detected = any(
        token in module38.lower()
        for token in (
            "purge_gap", "embargo", "purged", "horizon_gap", "label_end_date"
        )
    )

    if module38_forward_target and module38_contiguous_split and not module38_purge_detected:
        findings.append({
            "area": "module38_forecast_holdout",
            "status": "POTENTIAL_HORIZON_OVERLAP_LEAKAGE",
            "severity": "CRITICAL",
            "finding": "Forward-return targets are created with shift(-horizon), then training and validation are split contiguously without an explicit horizon purge/embargo. Training labels near the split can use prices inside the validation interval, so reported holdout accuracy is not sufficient evidence of clean out-of-sample skill until this is corrected or disproved with a date-level audit.",
        })
    else:
        findings.append({
            "area": "module38_forecast_holdout",
            "status": "NO_STATIC_OVERLAP_DEFECT_DETECTED",
            "severity": "INFO",
            "finding": "Static audit did not detect the specific contiguous forward-label overlap pattern.",
        })

    module39_true_rolling_dates = not contains(
        module39,
        '"training_end_date":pd.Timestamp(forecasts["forecast_date"].max()).date()',
        '"testing_start_date":pd.Timestamp(forecasts["forecast_date"].max()).date()',
        '"testing_end_date":pd.Timestamp(forecasts["forecast_date"].max()).date()',
    )
    module39_uses_validation_rows_as_folds = contains(
        module39,
        'for (asset,horizon),group in validation.groupby',
        'test=group.iloc[fold*fold_size:min((fold+1)*fold_size,n)]',
    )

    if (not module39_true_rolling_dates) and module39_uses_validation_rows_as_folds:
        findings.append({
            "area": "module39_rolling_origin_validation",
            "status": "NOT_TRUE_ROLLING_ORIGIN",
            "severity": "CRITICAL",
            "finding": "The table named rolling-origin validation partitions Module 38 model-validation summary rows and assigns training/test dates from the current forecast date rather than reconstructing chronological train/test origins. These rows must not be treated as independent rolling-origin evidence.",
        })
    else:
        findings.append({
            "area": "module39_rolling_origin_validation",
            "status": "STATIC_REVIEW_PASSED",
            "severity": "INFO",
            "finding": "The specific pseudo-rolling pattern was not detected.",
        })

    module39_calibration_proxy = contains(
        module39,
        'directional=(subset["directional_accuracy_pct"]/100)',
        'observed=(directional>=0.5).astype(int).to_numpy()',
        'raw=np.repeat(float(forecast["probability_positive"]),len(subset))',
    )
    if module39_calibration_proxy:
        findings.append({
            "area": "module39_probability_calibration",
            "status": "PROXY_NOT_REALIZED_OUTCOME_CALIBRATION",
            "severity": "HIGH",
            "finding": "Calibration converts model-level directional-accuracy summaries into binary observed labels and repeats the current forecast probability. It is not direct calibration against historical realized positive/negative outcomes and should not be interpreted as such.",
        })

    module44_forward_only = contains(
        module44,
        'due = (pd.Timestamp(rec_date) + pd.Timedelta(days=horizon)).date()',
        'realized = self.price_on_or_after(asset, due) if due <= today else None',
        'status = "PENDING"',
        'status = "MATURED"',
    )
    findings.append({
        "area": "module44_live_decision_outcomes",
        "status": "FORWARD_OUTCOME_TRACKING_SUPPORTED" if module44_forward_only else "REVIEW_REQUIRED",
        "severity": "INFO" if module44_forward_only else "HIGH",
        "finding": "Module 44 matures decisions only after their horizon due date and otherwise keeps them pending." if module44_forward_only else "Expected forward-only maturity guard was not detected.",
    })

    con = duckdb.connect(str(db), read_only=True)
    try:
        db_evidence = {
            "module44": con.execute(
                "SELECT outcome_status, COUNT(*) rows FROM m44_decision_outcomes GROUP BY 1 ORDER BY 1"
            ).fetchall(),
            "module39_latest_date_integrity": con.execute(
                """
                SELECT horizon_days,
                       COUNT(*) rows,
                       COUNT(DISTINCT training_end_date) training_end_dates,
                       COUNT(DISTINCT testing_start_date) testing_start_dates,
                       COUNT(DISTINCT testing_end_date) testing_end_dates,
                       MIN(training_end_date), MAX(training_end_date),
                       MIN(testing_start_date), MAX(testing_start_date)
                FROM latest_m39_rolling_origin_validation
                GROUP BY horizon_days ORDER BY horizon_days
                """
            ).fetchall(),
            "signal_forward_completed": con.execute(
                "SELECT COUNT(*) FROM signal_forward_performance WHERE completed=TRUE"
            ).fetchone()[0],
        }
    finally:
        con.close()

    db_after = sha256(db)
    require(db_before == db_after, "Read-only audit changed the database")

    critical = [f for f in findings if f["severity"] == "CRITICAL"]
    high = [f for f in findings if f["severity"] == "HIGH"]
    conclusion = (
        "NATIVE_PREDICTIVE_SKILL_NOT_CERTIFIED"
        if critical or high
        else "POINT_IN_TIME_SEMANTICS_SUPPORTED_FOR_FURTHER_SKILL_EVALUATION"
    )

    payload = {
        "status": "CRYPTO_NATIVE_POINT_IN_TIME_SEMANTICS_AUDIT_COMPLETE",
        "source_commit": args.source_commit,
        "database": str(db),
        "read_only": True,
        "database_unchanged": True,
        "findings": findings,
        "critical_findings": len(critical),
        "high_findings": len(high),
        "database_evidence": db_evidence,
        "conclusion": conclusion,
        "next_gate": "REMEDIATE_OR_DISPROVE_VALIDATION_SEMANTIC_DEFECTS_BEFORE_PREDICTIVE_SKILL_CERTIFICATION",
    }
    print(json.dumps(payload, indent=2, default=str))
    print("CRYPTO_NATIVE_POINT_IN_TIME_SEMANTICS_AUDIT=COMPLETE")
    print(f"CONCLUSION={conclusion}")
    print("DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=REMEDIATE_OR_DISPROVE_VALIDATION_SEMANTIC_DEFECTS_BEFORE_PREDICTIVE_SKILL_CERTIFICATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
