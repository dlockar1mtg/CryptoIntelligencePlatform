from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE38 = ROOT / "crypto_platform" / "module38.py"
MODULE39 = ROOT / "crypto_platform" / "module39.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one source anchor, found {count}")
    return text.replace(old, new, 1)


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def remediate_module38(text: str) -> str:
    text = replace_once(
        text,
        ");\n\nCREATE TABLE IF NOT EXISTS m38_asset_forecasts(",
        ");\n\nALTER TABLE module38_runs ADD COLUMN IF NOT EXISTS methodology_generation VARCHAR;\n\nCREATE TABLE IF NOT EXISTS m38_asset_forecasts(",
        "module38 methodology column",
    )
    text = replace_once(
        text,
        "]\n\n\ndef utcnow():",
        "]\n\nPREDICTIVE_METHODOLOGY_GENERATION = \"M38_PURGED_FEATURE_STABLE_V1\"\n\n\ndef utcnow():",
        "module38 generation constant",
    )
    text = replace_once(
        text,
        "            [\n                self.run_id,\n                self.source_m37,\n                self.source_m30,\n                self.started,\n            ],\n        )\n\n        try:\n",
        "            [\n                self.run_id,\n                self.source_m37,\n                self.source_m30,\n                self.started,\n            ],\n        )\n        self.conn.execute(\n            \"UPDATE module38_runs SET methodology_generation=? WHERE run_id=?\",\n            [PREDICTIVE_METHODOLOGY_GENERATION, self.run_id],\n        )\n\n        try:\n",
        "module38 generation persistence",
    )
    return text


def remediate_module39(text: str) -> str:
    text = replace_once(
        text,
        "from crypto_platform.module38 import MODULE38_SCHEMA\n",
        "from crypto_platform.module38 import (\n    MODULE38_SCHEMA,\n    PREDICTIVE_METHODOLOGY_GENERATION,\n)\n",
        "module39 generation import",
    )
    text = replace_once(
        text,
        "        row=self.conn.execute(\n            \"SELECT run_id FROM module38_runs WHERE status='SUCCESS' \"\n            \"ORDER BY started_at_utc DESC LIMIT 1\"\n        ).fetchone()\n        if row is None:\n            raise RuntimeError(\"A successful Module 38 run is required.\")\n        self.source_m38=str(row[0])\n",
        "        row=self.conn.execute(\n            \"SELECT run_id, methodology_generation FROM module38_runs WHERE status='SUCCESS' \"\n            \"ORDER BY started_at_utc DESC LIMIT 1\"\n        ).fetchone()\n        if row is None:\n            raise RuntimeError(\"A successful Module 38 run is required.\")\n        self.source_m38=str(row[0])\n        self.methodology_generation=row[1]\n        if self.methodology_generation is None:\n            raise RuntimeError(\"Latest successful Module 38 run is legacy and cannot be used as a generation-aware Module 39 source.\")\n        if str(self.methodology_generation) != PREDICTIVE_METHODOLOGY_GENERATION:\n            raise RuntimeError(\"Unexpected Module 38 predictive methodology generation.\")\n",
        "module39 source generation gate",
    )
    text = replace_once(
        text,
        "    def historical_forecasts(self):\n",
        "    def stability_attributions(self):\n        return self.conn.execute(\n            \"\"\"\n            SELECT f.* EXCLUDE(methodology_generation, started_at_utc)\n            FROM (\n                SELECT a.*, r.methodology_generation, r.started_at_utc\n                FROM m38_forecast_attribution a\n                JOIN module38_runs r USING(run_id)\n                WHERE r.status='SUCCESS'\n                  AND r.methodology_generation=?\n                QUALIFY row_number() OVER(\n                    PARTITION BY a.forecast_date,a.asset_id,a.horizon_days,a.driver_key\n                    ORDER BY r.started_at_utc DESC,a.calculated_at_utc DESC\n                )=1\n            ) f\n            ORDER BY forecast_date,asset_id,horizon_days,driver_key\n            \"\"\",\n            [self.methodology_generation],\n        ).fetchdf()\n\n    def historical_forecasts(self):\n",
        "module39 distinct-date generation stability source",
    )
    old_drift = '''        previous=self.conn.execute(\n            \"\"\"\n            SELECT * FROM m38_asset_forecasts\n            WHERE run_id<>?\n            QUALIFY row_number() OVER(\n                PARTITION BY asset_id,horizon_days\n                ORDER BY forecast_date DESC,calculated_at_utc DESC\n            )=1\n            \"\"\",[self.source_m38]\n        ).fetchdf()\n'''
    new_drift = '''        previous=self.conn.execute(\n            \"\"\"\n            SELECT f.*\n            FROM m38_asset_forecasts f\n            JOIN module38_runs r USING(run_id)\n            WHERE f.run_id<>?\n              AND r.status='SUCCESS'\n              AND r.methodology_generation=?\n              AND f.forecast_date < (\n                  SELECT MAX(forecast_date)\n                  FROM m38_asset_forecasts\n                  WHERE run_id=?\n              )\n            QUALIFY row_number() OVER(\n                PARTITION BY f.asset_id,f.horizon_days\n                ORDER BY f.forecast_date DESC,f.calculated_at_utc DESC\n            )=1\n            \"\"\",[self.source_m38,self.methodology_generation,self.source_m38]\n        ).fetchdf()\n'''
    text = replace_once(text, old_drift, new_drift, "module39 same-generation drift baseline")
    old_empty = '''            if prior.empty:\n                return_change=prob_change=conf_change=width_change=0.0\n                prior_date=row.forecast_date\n            else:\n'''
    new_empty = '''            if prior.empty:\n                rows.append({\n                    \"run_id\":self.run_id,\"asset_id\":row.asset_id,\n                    \"horizon_days\":int(row.horizon_days),\n                    \"current_forecast_date\":row.forecast_date,\n                    \"prior_forecast_date\":None,\n                    \"return_forecast_change_pct\":np.nan,\n                    \"probability_change\":np.nan,\"confidence_change\":np.nan,\n                    \"interval_width_change_pct\":np.nan,\n                    \"model_weight_distance\":np.nan,\n                    \"attribution_rank_change\":np.nan,\n                    \"drift_score\":np.nan,\"drift_status\":\"BASELINE_REQUIRED\",\n                    \"calculated_at_utc\":utcnow(),\n                })\n                continue\n            else:\n'''
    text = replace_once(text, old_empty, new_empty, "module39 baseline-required drift status")
    text = replace_once(
        text,
        "            attribution=self.attributions()\n            replay_bundle=self.true_replay()\n",
        "            attribution=self.attributions()\n            stability_attribution=self.stability_attributions()\n            replay_bundle=self.true_replay()\n",
        "module39 stability history load",
    )
    text = replace_once(
        text,
        "            stability=self.stability(attribution)\n",
        "            stability=self.stability(stability_attribution)\n",
        "module39 stability history use",
    )
    text = replace_once(
        text,
        "            stable_pct=float(\n                (evidence_ready[\"stability_score\"]>=65).mean()*100\n            ) if not evidence_ready.empty else 0.0\n            current_drift=(\n                \"CRITICAL\" if (drift[\"drift_status\"]==\"CRITICAL\").any()\n                else \"WARNING\" if (drift[\"drift_status\"]==\"WARNING\").any()\n                else \"STABLE\"\n            )\n",
        "            stable_pct=float(\n                (evidence_ready[\"stability_score\"]>=65).mean()*100\n            ) if not evidence_ready.empty else np.nan\n            current_drift=(\n                \"CRITICAL\" if (drift[\"drift_status\"]==\"CRITICAL\").any()\n                else \"WARNING\" if (drift[\"drift_status\"]==\"WARNING\").any()\n                else \"BASELINE_REQUIRED\" if (drift[\"drift_status\"]==\"BASELINE_REQUIRED\").any()\n                else \"STABLE\"\n            )\n            monitoring_evidence_ready=bool(\n                not evidence_ready.empty\n                and current_drift != \"BASELINE_REQUIRED\"\n            )\n",
        "module39 explicit insufficient stability and drift semantics",
    )
    text = replace_once(
        text,
        "            evidence_ready=bool(\n                len(scorecards)>=minimum_scorecards\n                and supported_calibration[\"validation_rows\"].sum()\n                >=int(\n                    self.cfg.get(\n                        \"minimum_total_calibration_rows\",\n                        180,\n                    )\n                )\n            )\n",
        "            evidence_ready=bool(\n                len(scorecards)>=minimum_scorecards\n                and supported_calibration[\"validation_rows\"].sum()\n                >=int(\n                    self.cfg.get(\n                        \"minimum_total_calibration_rows\",\n                        180,\n                    )\n                )\n                and monitoring_evidence_ready\n            )\n",
        "module39 monitoring evidence advancement block",
    )
    return text


def main() -> int:
    module38_before = read_text(MODULE38)
    module39_before = read_text(MODULE39)
    if "PREDICTIVE_METHODOLOGY_GENERATION" in module38_before:
        raise RuntimeError("Module 38 generation-aware remediation appears to be already applied")
    if "def stability_attributions(self):" in module39_before:
        raise RuntimeError("Module 39 generation-aware remediation appears to be already applied")

    module38_after = remediate_module38(module38_before)
    module39_after = remediate_module39(module39_before)
    write_text(MODULE38, module38_after)
    write_text(MODULE39, module39_after)

    print("CRYPTO_MODULE39_GENERATION_AWARE_SEMANTICS_REMEDIATION=PASS")
    print(f"UPDATED_FILE={MODULE38}")
    print(f"UPDATED_FILE={MODULE39}")
    print("METHODOLOGY_GENERATION_PERSISTED=TRUE")
    print("LEGACY_RUNS_NONCOMPARABLE=TRUE")
    print("STABILITY_DISTINCT_FORECAST_DATES_ONLY=TRUE")
    print("DRIFT_SAME_GENERATION_EARLIER_DATE_ONLY=TRUE")
    print("INSUFFICIENT_STABILITY_REPRESENTED_AS_MISSING=TRUE")
    print("MISSING_DRIFT_BASELINE_STATUS=BASELINE_REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
