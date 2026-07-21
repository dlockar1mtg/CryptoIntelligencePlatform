from __future__ import annotations
import json

def candidate_row(experiment_id, candidate, created_at):
    p=candidate["parameters"]
    return {
        "experiment_id": experiment_id,
        "candidate_id": candidate["candidate_id"],
        "parameter_hash": candidate["parameter_hash"],
        "parameters_json": json.dumps(p, sort_keys=True),
        "generation_seed": candidate["generation_seed"],
        "status": "GENERATED",
        "created_at_utc": created_at,
    }
