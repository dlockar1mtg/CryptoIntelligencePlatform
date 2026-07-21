from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "crypto_platform"
OUTPUT_ROOT = ROOT / "docs" / "integration" / "robustness" / "focused"

TARGET_MODULES = [7, 15, 23, 24, 30, 32, 33, 38, 40, 44]

KEY_TERMS = {
    "walk_forward": (
        "walk_forward",
        "out_of_sample",
        "oos",
        "train_start",
        "train_end",
        "test_start",
        "test_end",
    ),
    "leakage_protection": (
        "lookahead",
        "leakage",
        "shift",
        "lag",
        "cutoff",
        "as_of",
    ),
    "benchmarks": (
        "benchmark",
        "buy_and_hold",
        "equal_weight",
        "btc",
    ),
    "costs": (
        "transaction_cost",
        "slippage",
        "fee",
        "turnover",
    ),
    "calibration": (
        "brier",
        "calibration",
        "ece",
        "probability",
    ),
    "risk": (
        "drawdown",
        "sharpe",
        "sortino",
        "calmar",
        "volatility",
    ),
    "drift": (
        "drift",
        "degradation",
        "decay",
        "stability",
    ),
    "promotion": (
        "promotion",
        "promoted",
        "champion",
        "challenger",
        "rollback",
    ),
    "audit": (
        "run_id",
        "model_version",
        "config_version",
        "input_hash",
        "audit",
    ),
}


@dataclass(frozen=True)
class FunctionFinding:
    module_number: int
    module_path: str
    function_name: str
    start_line: int
    end_line: int
    matched_categories: list[str]


def source_segment(
    lines: list[str],
    start_line: int,
    end_line: int,
) -> str:
    return "\n".join(lines[start_line - 1:end_line])


def inspect_module(module_number: int) -> list[FunctionFinding]:
    path = PACKAGE_ROOT / f"module{module_number}.py"
    source = path.read_text(encoding="utf-8-sig")
    lines = source.splitlines()
    tree = ast.parse(source, filename=str(path))

    findings: list[FunctionFinding] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        end_line = getattr(node, "end_lineno", node.lineno)
        segment = source_segment(lines, node.lineno, end_line).lower()

        matched = sorted(
            category
            for category, terms in KEY_TERMS.items()
            if any(term.lower() in segment for term in terms)
        )

        if not matched:
            continue

        findings.append(
            FunctionFinding(
                module_number=module_number,
                module_path=path.relative_to(ROOT).as_posix(),
                function_name=node.name,
                start_line=node.lineno,
                end_line=end_line,
                matched_categories=matched,
            )
        )

    return sorted(
        findings,
        key=lambda item: (
            item.module_number,
            item.start_line,
        ),
    )


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    findings: list[FunctionFinding] = []

    for module_number in TARGET_MODULES:
        findings.extend(inspect_module(module_number))

    json_path = OUTPUT_ROOT / "focused_function_inventory.json"
    markdown_path = OUTPUT_ROOT / "FOCUSED_ROBUSTNESS_FUNCTIONS.md"

    json_path.write_text(
        json.dumps(
            [asdict(item) for item in findings],
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Focused Crypto Robustness Function Inventory",
        "",
        f"- Modules inspected: {len(TARGET_MODULES)}",
        f"- Relevant functions identified: {len(findings)}",
        "",
        "| Module | Function | Lines | Categories |",
        "|---:|---|---:|---|",
    ]

    for item in findings:
        categories = ", ".join(item.matched_categories)
        lines.append(
            f"| {item.module_number} "
            f"| `{item.function_name}` "
            f"| {item.start_line}-{item.end_line} "
            f"| {categories} |"
        )

    markdown_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("Focused Crypto Robustness Function Inventory")
    print("=" * 48)
    print(f"Modules inspected: {len(TARGET_MODULES)}")
    print(f"Relevant functions identified: {len(findings)}")
    print(f"Report: {markdown_path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())