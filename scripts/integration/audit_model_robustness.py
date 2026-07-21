from __future__ import annotations

import ast
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "crypto_platform"
OUTPUT_ROOT = ROOT / "docs" / "integration" / "robustness"

MODULE_MIN = 6
MODULE_MAX = 44


CAPABILITIES: dict[str, tuple[str, ...]] = {
    "walk_forward_validation": (
        "walk_forward",
        "walk-forward",
        "rolling_window",
        "expanding_window",
        "out_of_sample",
        "out-of-sample",
        "oos",
    ),
    "time_based_split": (
        "time_series_split",
        "timeseriessplit",
        "train_start",
        "train_end",
        "test_start",
        "test_end",
        "validation_start",
        "validation_end",
        "cutoff_date",
        "as_of_date",
    ),
    "benchmark_comparison": (
        "benchmark",
        "buy_and_hold",
        "buy-and-hold",
        "equal_weight",
        "market_cap_weight",
        "btc_hold",
        "bitcoin_hold",
        "baseline_return",
    ),
    "transaction_costs": (
        "transaction_cost",
        "trading_fee",
        "commission",
        "slippage",
        "bid_ask",
        "spread_bps",
        "fee_bps",
        "turnover_cost",
    ),
    "drawdown_analysis": (
        "max_drawdown",
        "maximum_drawdown",
        "drawdown",
        "underwater",
        "peak_to_trough",
    ),
    "risk_adjusted_metrics": (
        "sharpe",
        "sortino",
        "calmar",
        "information_ratio",
        "volatility",
        "downside_deviation",
    ),
    "forecast_calibration": (
        "brier",
        "calibration",
        "expected_calibration_error",
        "ece",
        "reliability_curve",
        "probability_calibration",
    ),
    "statistical_confidence": (
        "bootstrap",
        "confidence_interval",
        "confidence level",
        "p_value",
        "p-value",
        "permutation",
        "monte_carlo",
        "resample",
    ),
    "regime_validation": (
        "bull",
        "bear",
        "sideways",
        "regime",
        "high_volatility",
        "low_volatility",
        "risk_on",
        "risk_off",
    ),
    "sensitivity_testing": (
        "sensitivity",
        "parameter_grid",
        "grid_search",
        "threshold_grid",
        "scenario",
        "stress_test",
        "stress test",
        "perturb",
    ),
    "feature_drift": (
        "feature_drift",
        "population_stability",
        "psi",
        "distribution_shift",
        "feature_shift",
    ),
    "prediction_drift": (
        "prediction_drift",
        "score_drift",
        "probability_drift",
        "output_drift",
    ),
    "performance_drift": (
        "performance_drift",
        "model_decay",
        "performance_decay",
        "degradation",
        "rolling_accuracy",
        "rolling_brier",
    ),
    "lookahead_protection": (
        "lookahead",
        "look_ahead",
        "future_leak",
        "data_leak",
        "leakage",
        "lagged",
        "shift(1",
        "shift(periods=1",
        "available_at",
        "known_at",
    ),
    "deterministic_replay": (
        "deterministic",
        "replay",
        "random_seed",
        "random_state",
        "seed",
        "input_snapshot",
        "configuration_snapshot",
    ),
    "auditability": (
        "audit",
        "run_id",
        "model_version",
        "config_version",
        "decision_id",
        "input_hash",
        "created_at",
        "generated_at",
    ),
    "promotion_guardrails": (
        "promotion",
        "promoted",
        "rollback",
        "champion",
        "challenger",
        "minimum_improvement",
        "promotion_threshold",
    ),
    "universal_contract": (
        "asset_master",
        "recommendations",
        "forecasts",
        "risk_metrics",
        "platform_status",
        "export_manifest",
        "portfolio_positions",
        "universal",
    ),
}


CRITICAL_CAPABILITIES = {
    "walk_forward_validation",
    "time_based_split",
    "benchmark_comparison",
    "transaction_costs",
    "drawdown_analysis",
    "risk_adjusted_metrics",
    "forecast_calibration",
    "lookahead_protection",
    "deterministic_replay",
    "auditability",
}


LEAKAGE_RISK_PATTERNS: dict[str, str] = {
    "random_train_test_split": r"\btrain_test_split\s*\(",
    "full_sample_scaler_fit": (
        r"\b(?:StandardScaler|MinMaxScaler|RobustScaler)"
        r"\s*\([^)]*\)\s*\.fit(?:_transform)?\s*\("
    ),
    "negative_shift": r"\.shift\s*\(\s*-\d+",
    "future_named_variable": (
        r"\b(?:future_return|future_price|next_return|next_price|"
        r"forward_return|target_future)\b"
    ),
    "global_normalization": (
        r"\b(?:mean|std|min|max)\s*\(\s*\)"
    ),
}


@dataclass(frozen=True)
class CapabilityEvidence:
    module_number: int
    module_path: str
    capability: str
    evidence_count: int
    evidence_terms: list[str]
    function_names: list[str]
    table_names: list[str]


@dataclass(frozen=True)
class LeakageFinding:
    module_number: int
    module_path: str
    risk_type: str
    line_number: int
    line_text: str


@dataclass(frozen=True)
class ModuleSummary:
    module_number: int
    module_path: str
    function_count: int
    class_count: int
    table_count: int
    detected_capabilities: list[str]
    critical_capabilities_detected: list[str]
    leakage_risk_count: int


def module_path(module_number: int) -> Path:
    return PACKAGE_ROOT / f"module{module_number}.py"


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def parse_tree(path: Path, source: str) -> ast.Module:
    return ast.parse(source, filename=str(path))


def collect_function_names(tree: ast.Module) -> list[str]:
    return sorted(
        {
            node.name
            for node in ast.walk(tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }
    )


def collect_class_names(tree: ast.Module) -> list[str]:
    return sorted(
        {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        }
    )


def collect_table_names(source: str) -> list[str]:
    patterns = (
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_.]+)",
        r"INSERT\s+INTO\s+([A-Za-z0-9_.]+)",
        r"FROM\s+([A-Za-z0-9_.]+)",
        r"JOIN\s+([A-Za-z0-9_.]+)",
    )

    tables: set[str] = set()

    for pattern in patterns:
        for match in re.finditer(pattern, source, flags=re.IGNORECASE):
            tables.add(match.group(1))

    return sorted(tables)


def detect_capabilities(
    module_number: int,
    path: Path,
    source: str,
    function_names: list[str],
    table_names: list[str],
) -> list[CapabilityEvidence]:
    searchable = source.lower()
    evidence: list[CapabilityEvidence] = []

    for capability, terms in CAPABILITIES.items():
        matched_terms = sorted(
            {
                term
                for term in terms
                if term.lower() in searchable
            }
        )

        if not matched_terms:
            continue

        count = sum(
            searchable.count(term.lower())
            for term in matched_terms
        )

        evidence.append(
            CapabilityEvidence(
                module_number=module_number,
                module_path=path.relative_to(ROOT).as_posix(),
                capability=capability,
                evidence_count=count,
                evidence_terms=matched_terms,
                function_names=function_names,
                table_names=table_names,
            )
        )

    return evidence


def detect_leakage_risks(
    module_number: int,
    path: Path,
    source: str,
) -> list[LeakageFinding]:
    findings: list[LeakageFinding] = []
    lines = source.splitlines()

    for risk_type, pattern in LEAKAGE_RISK_PATTERNS.items():
        regex = re.compile(pattern, flags=re.IGNORECASE)

        for line_number, line in enumerate(lines, start=1):
            if not regex.search(line):
                continue

            findings.append(
                LeakageFinding(
                    module_number=module_number,
                    module_path=path.relative_to(ROOT).as_posix(),
                    risk_type=risk_type,
                    line_number=line_number,
                    line_text=line.strip()[:240],
                )
            )

    return findings


def inspect_modules() -> tuple[
    list[ModuleSummary],
    list[CapabilityEvidence],
    list[LeakageFinding],
]:
    summaries: list[ModuleSummary] = []
    all_evidence: list[CapabilityEvidence] = []
    leakage_findings: list[LeakageFinding] = []

    for module_number in range(MODULE_MIN, MODULE_MAX + 1):
        path = module_path(module_number)

        if not path.is_file():
            continue

        source = read_source(path)
        tree = parse_tree(path, source)

        function_names = collect_function_names(tree)
        class_names = collect_class_names(tree)
        table_names = collect_table_names(source)

        evidence = detect_capabilities(
            module_number=module_number,
            path=path,
            source=source,
            function_names=function_names,
            table_names=table_names,
        )

        module_leakage = detect_leakage_risks(
            module_number=module_number,
            path=path,
            source=source,
        )

        all_evidence.extend(evidence)
        leakage_findings.extend(module_leakage)

        detected = sorted(
            {item.capability for item in evidence}
        )

        summaries.append(
            ModuleSummary(
                module_number=module_number,
                module_path=path.relative_to(ROOT).as_posix(),
                function_count=len(function_names),
                class_count=len(class_names),
                table_count=len(table_names),
                detected_capabilities=detected,
                critical_capabilities_detected=sorted(
                    set(detected) & CRITICAL_CAPABILITIES
                ),
                leakage_risk_count=len(module_leakage),
            )
        )

    return summaries, all_evidence, leakage_findings


def write_json(path: Path, records: list[Any]) -> None:
    path.write_text(
        json.dumps(
            [asdict(record) for record in records],
            indent=2,
        ),
        encoding="utf-8",
    )


def write_capability_csv(
    path: Path,
    evidence: list[CapabilityEvidence],
) -> None:
    fieldnames = [
        "module_number",
        "module_path",
        "capability",
        "evidence_count",
        "evidence_terms",
        "function_names",
        "table_names",
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for item in evidence:
            row = asdict(item)
            row["evidence_terms"] = "; ".join(item.evidence_terms)
            row["function_names"] = "; ".join(item.function_names)
            row["table_names"] = "; ".join(item.table_names)
            writer.writerow(row)


def write_leakage_csv(
    path: Path,
    findings: list[LeakageFinding],
) -> None:
    fieldnames = [
        "module_number",
        "module_path",
        "risk_type",
        "line_number",
        "line_text",
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for finding in findings:
            writer.writerow(asdict(finding))


def write_markdown(
    path: Path,
    summaries: list[ModuleSummary],
    evidence: list[CapabilityEvidence],
    leakage_findings: list[LeakageFinding],
) -> None:
    detected_by_capability: dict[str, list[int]] = {
        capability: []
        for capability in CAPABILITIES
    }

    for item in evidence:
        detected_by_capability[item.capability].append(
            item.module_number
        )

    missing_critical = sorted(
        capability
        for capability in CRITICAL_CAPABILITIES
        if not detected_by_capability[capability]
    )

    lines = [
        "# Crypto Robustness Capability Audit",
        "",
        "This report identifies source-code evidence. It does not by itself",
        "certify that a capability is correctly implemented.",
        "",
        f"- Modules inspected: {len(summaries)}",
        f"- Capability categories: {len(CAPABILITIES)}",
        f"- Evidence records: {len(evidence)}",
        f"- Potential leakage findings: {len(leakage_findings)}",
        f"- Missing critical capability categories: {len(missing_critical)}",
        "",
        "## Capability coverage",
        "",
        "| Capability | Modules with evidence | Critical gate |",
        "|---|---|---|",
    ]

    for capability in CAPABILITIES:
        modules = sorted(set(detected_by_capability[capability]))
        module_text = (
            ", ".join(str(number) for number in modules)
            if modules
            else "None detected"
        )
        critical = "Yes" if capability in CRITICAL_CAPABILITIES else "No"

        lines.append(
            f"| `{capability}` | {module_text} | {critical} |"
        )

    lines.extend(
        [
            "",
            "## Missing critical categories",
            "",
        ]
    )

    if missing_critical:
        for capability in missing_critical:
            lines.append(f"- `{capability}`")
    else:
        lines.append(
            "Source-code evidence was detected for every critical category."
        )

    lines.extend(
        [
            "",
            "## Potential leakage findings",
            "",
        ]
    )

    if leakage_findings:
        lines.append(
            "| Module | Risk type | Line | Source text |"
        )
        lines.append("|---:|---|---:|---|")

        for finding in leakage_findings:
            escaped = finding.line_text.replace("|", "\\|")
            lines.append(
                f"| {finding.module_number} "
                f"| `{finding.risk_type}` "
                f"| {finding.line_number} "
                f"| `{escaped}` |"
            )
    else:
        lines.append(
            "No configured static leakage-risk patterns were detected."
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Detected evidence means a term or implementation pattern exists.",
            "- It does not prove correct time ordering or true out-of-sample use.",
            "- Every critical capability requires targeted code inspection.",
            "- Every performance claim requires reproducible historical execution.",
            "- Potential leakage findings require manual review before certification.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    summaries, evidence, leakage_findings = inspect_modules()

    write_json(
        OUTPUT_ROOT / "module_robustness_summary.json",
        summaries,
    )
    write_json(
        OUTPUT_ROOT / "capability_evidence.json",
        evidence,
    )
    write_json(
        OUTPUT_ROOT / "potential_leakage_findings.json",
        leakage_findings,
    )

    write_capability_csv(
        OUTPUT_ROOT / "capability_evidence.csv",
        evidence,
    )
    write_leakage_csv(
        OUTPUT_ROOT / "potential_leakage_findings.csv",
        leakage_findings,
    )
    write_markdown(
        OUTPUT_ROOT / "CRYPTO_ROBUSTNESS_CAPABILITY_AUDIT.md",
        summaries,
        evidence,
        leakage_findings,
    )

    detected_capabilities = {
        item.capability
        for item in evidence
    }

    missing_critical = sorted(
        CRITICAL_CAPABILITIES - detected_capabilities
    )

    print("Crypto Robustness Capability Audit")
    print("=" * 40)
    print(f"Modules inspected: {len(summaries)}")
    print(f"Capability evidence records: {len(evidence)}")
    print(f"Potential leakage findings: {len(leakage_findings)}")
    print(f"Missing critical categories: {len(missing_critical)}")

    if missing_critical:
        print()
        print("Missing critical categories:")
        for capability in missing_critical:
            print(f"  - {capability}")

    print()
    print(
        "Report: "
        "docs/integration/robustness/"
        "CRYPTO_ROBUSTNESS_CAPABILITY_AUDIT.md"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())