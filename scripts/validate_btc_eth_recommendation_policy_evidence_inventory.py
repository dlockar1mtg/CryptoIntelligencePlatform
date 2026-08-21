from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path

EXPECTED_V4_7D_SHA256 = "fe82f2b8cdfe817bfbb825cd2d97eb7d02711c8d1a2d3e5b3daf6c17fe756a48"
EXPECTED_V4_365_AUX_SHA256 = "f6a57ac6adefe5a0b187d9a3310b6d1cb4a7af20068c1eea779ca9b9d1b97735"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--v4-7d-final-results", required=True)
    parser.add_argument("--v4-365d-aux-results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runner = Path(args.runner).resolve()
    design = Path(args.design).resolve()
    final7 = Path(args.v4_7d_final_results).resolve()
    aux365 = Path(args.v4_365d_aux_results).resolve()
    output = Path(args.output).resolve()

    for path in (runner, design, final7, aux365):
        require(path.is_file(), f"Required validation input missing: {path}")
    require(not output.exists(), "Inventory output already exists; preflight must run before execution")
    require(sha256(final7) == EXPECTED_V4_7D_SHA256, "Unexpected V4 7d result hash")
    require(sha256(aux365) == EXPECTED_V4_365_AUX_SHA256, "Unexpected V4 365d auxiliary result hash")

    source = runner.read_text(encoding="utf-8")
    ast.parse(source)
    design_text = design.read_text(encoding="utf-8")

    for required in (
        "CRYPTO_BTC_ETH_RECOMMENDATION_POLICY_VALIDATION_V1",
        "BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY",
        "No policy score or threshold decision may be produced by the inventory step",
    ):
        require(required in design_text, f"Design missing required control: {required}")

    for required in (
        'duckdb.connect(str(database), read_only=True)',
        'ASSETS = ("bitcoin", "ethereum")',
        'HORIZONS = (7, 30, 90, 180)',
        '"policy_scoring_performed": False',
        '"threshold_optimization_performed": False',
        '"policy_winner_selected": False',
        '"production_policy_changed": False',
        '"source_database_modified": False',
        'outcome_due_date',
        'exact_price_available',
    ):
        require(required in source, f"Inventory runner missing required boundary: {required}")

    prohibited = (
        "ACTION_POSITION",
        "strategy_return_pct =",
        "action_value_score",
        "choose_winner",
        "fit_predict",
        "model.fit(",
        "INSERT INTO",
        "INSERT OR REPLACE",
        "UPDATE ",
        "DELETE FROM",
    )
    for token in prohibited:
        require(token not in source, f"Inventory runner contains prohibited scoring/write behavior: {token}")

    print("CRYPTO_BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY_VALIDATION=PASS")
    print("PRIMARY_ASSETS=bitcoin,ethereum")
    print("EXACT_OUTCOME_HORIZONS=7,30,90,180")
    print("DATABASE_OPEN_MODE=READ_ONLY")
    print("INVENTORY_ONLY=TRUE")
    print("POLICY_SCORING_ALLOWED=FALSE")
    print("THRESHOLD_OPTIMIZATION_ALLOWED=FALSE")
    print("POLICY_WINNER_SELECTION_ALLOWED=FALSE")
    print("PRODUCTION_POLICY_CHANGE_ALLOWED=FALSE")
    print("INVENTORY_EXECUTION_PERFORMED=FALSE")
    print("NEXT_GATE=AUTHORIZE_BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
