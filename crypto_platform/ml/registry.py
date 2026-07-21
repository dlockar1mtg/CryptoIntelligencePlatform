from __future__ import annotations

import json
import platform
import uuid
from datetime import datetime, timezone

import sklearn


EXPERIMENT_REGISTRY_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS ml_experiment_registry(
    experiment_id VARCHAR PRIMARY KEY,
    module_name VARCHAR,
    release_version VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    feature_set_json VARCHAR,
    hyperparameters_json VARCHAR,
    validation_metrics_json VARCHAR,
    calibration_metrics_json VARCHAR,
    promotion_status VARCHAR,
    python_version VARCHAR,
    sklearn_version VARCHAR,
    notes VARCHAR
);
"""


def utcnow():
    return datetime.now(timezone.utc)


def start_experiment(
    conn,
    module_name: str,
    release_version: str,
    feature_set: list[str],
    hyperparameters: dict,
) -> str:
    conn.execute(EXPERIMENT_REGISTRY_SCHEMA)
    experiment_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO ml_experiment_registry VALUES(
            ?,?,?,?,NULL,'RUNNING',?,?,NULL,NULL,
            'RESEARCH',?,?,NULL
        )
        """,
        [
            experiment_id,
            module_name,
            release_version,
            utcnow(),
            json.dumps(feature_set),
            json.dumps(hyperparameters, sort_keys=True),
            platform.python_version(),
            sklearn.__version__,
        ],
    )
    return experiment_id


def complete_experiment(
    conn,
    experiment_id: str,
    status: str,
    validation_metrics: dict,
    calibration_metrics: dict,
    promotion_status: str,
    notes: str,
) -> None:
    conn.execute(
        """
        UPDATE ml_experiment_registry
        SET completed_at_utc=?,
            status=?,
            validation_metrics_json=?,
            calibration_metrics_json=?,
            promotion_status=?,
            notes=?
        WHERE experiment_id=?
        """,
        [
            utcnow(),
            status,
            json.dumps(validation_metrics, sort_keys=True),
            json.dumps(calibration_metrics, sort_keys=True),
            promotion_status,
            notes,
            experiment_id,
        ],
    )
