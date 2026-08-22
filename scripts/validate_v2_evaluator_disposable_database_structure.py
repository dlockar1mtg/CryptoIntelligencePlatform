from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_v2_native_context_holdout_evaluation.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(TARGET))

    temp_with_nodes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            expr = item.context_expr
            if (
                isinstance(expr, ast.Call)
                and isinstance(expr.func, ast.Attribute)
                and expr.func.attr == "TemporaryDirectory"
            ):
                temp_with_nodes.append(node)

    require(len(temp_with_nodes) == 1, f"Expected exactly one TemporaryDirectory block, found {len(temp_with_nodes)}")
    temp_with = temp_with_nodes[0]

    calls_inside = [n for n in ast.walk(temp_with) if isinstance(n, ast.Call)]
    names_inside = [call_name(n) for n in calls_inside]
    require("copy2" in names_inside, "shutil.copy2 is not inside TemporaryDirectory block")
    require("connect" in names_inside, "platform connect call is not inside TemporaryDirectory block")

    source_target_assignments = []
    temp_target_assignments = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        segment = ast.get_source_segment(text, node) or ""
        if 'os.environ["CRYPTO_DATABASE_PATH"]' in segment:
            if "str(source)" in segment:
                source_target_assignments.append(segment)
            if "str(temp_db)" in segment:
                temp_target_assignments.append(segment)

    require(not source_target_assignments, "Evaluator still targets source database directly")
    require(len(temp_target_assignments) == 1, f"Expected exactly one disposable database target assignment, found {len(temp_target_assignments)}")

    require('before_db = sha256(source)' in text, "Source DB pre-run hash missing")
    require('require(sha256(source) == before_db, "Source database changed during V2 holdout evaluation")' in text, "Source DB post-run immutability assertion missing")
    require('before_manifest = sha256(manifest_path)' in text, "Manifest pre-run hash missing")
    require('require(sha256(manifest_path) == before_manifest, "Frozen V2 manifest changed during evaluation")' in text, "Manifest post-run immutability assertion missing")

    print("CRYPTO_V2_EVALUATOR_DISPOSABLE_DATABASE_STRUCTURE_VALIDATION=PASS")
    print("TEMPORARY_DIRECTORY_BLOCKS=1")
    print("CONNECT_CALL_INSIDE_DISPOSABLE_SCOPE=TRUE")
    print("SOURCE_DATABASE_DIRECT_TARGET_ASSIGNMENTS=0")
    print("DISPOSABLE_DATABASE_TARGET_ASSIGNMENTS=1")
    print("SOURCE_AND_MANIFEST_IMMUTABILITY_ASSERTIONS=TRUE")
    print("NEXT_GATE=RUN_V2_RECOVERY_EVALUATION_ON_DISPOSABLE_DATABASE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
