"""Research-only modules run weekly; the UIP delivery chain runs every cycle and fails closed."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import textwrap

import duckdb
import pytest

from crypto_platform.production import registry as registry_module
from crypto_platform.production.hosted import evaluate_hosted_database, prepare_uip_delivery
from crypto_platform.production.orchestrator import (
    SKIPPED_WEEKLY,
    PipelineOptions,
    ProductionOrchestrator,
)
from crypto_platform.production.registry import (
    MODULE_REGISTRY,
    RESEARCH_ONLY_MODULES,
    UIP_DELIVERY_MODULES,
    ModuleSpec,
    active_modules,
    validate_registry,
    weekly_modules,
)
from tests.production.test_hosted import _build_database


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "crypto-production-cycle.yml"
EXPECTED_WEEKLY = {2, 3, 5, *range(7, 17), *range(18, 25), 26, 43, 44}

STUB_RUNNER = """
import os, pathlib, sys
number = os.environ["CRYPTO_PRODUCTION_MODULE"]
with pathlib.Path(os.environ["STUB_RUN_LOG"]).open("a", encoding="utf-8") as handle:
    handle.write(number + "\\n")
if number in os.environ.get("STUB_FAIL_MODULES", "").split(","):
    sys.exit(3)
"""


# --- registry ---------------------------------------------------------------------------


def test_weekly_set_is_exactly_the_research_only_modules() -> None:
    assert {spec.number for spec in weekly_modules()} == EXPECTED_WEEKLY
    assert set(RESEARCH_ONLY_MODULES) == EXPECTED_WEEKLY


def test_delivery_chain_runs_daily() -> None:
    by_number = {spec.number: spec for spec in MODULE_REGISTRY}
    assert UIP_DELIVERY_MODULES == (1, 6, 17, 25, *range(27, 43))
    for number in UIP_DELIVERY_MODULES:
        assert by_number[number].cadence == "daily"
        assert by_number[number].required is True
    active = {spec.number for spec in active_modules()}
    assert active == set(UIP_DELIVERY_MODULES) | EXPECTED_WEEKLY


def test_module_24_is_weekly_research() -> None:
    spec = next(item for item in MODULE_REGISTRY if item.number == 24)
    assert spec.weekly and spec.run_table == "module24_runs"


def test_registry_rejects_a_delivery_module_marked_weekly(monkeypatch) -> None:
    patched = tuple(
        ModuleSpec(**{**spec.__dict__, "cadence": "weekly"}) if spec.number == 39 else spec
        for spec in MODULE_REGISTRY
    )
    monkeypatch.setattr(registry_module, "MODULE_REGISTRY", patched)
    errors = validate_registry(ROOT)
    assert any("Module 39 feeds the UIP delivery" in error for error in errors)


def _written_tables(source: str) -> set[str]:
    pattern = re.compile(
        r"(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"|INSERT\s+(?:OR\s+REPLACE\s+)?INTO\s+)([a-z_][a-z0-9_]*)"
        r"|upsert\(\s*['\"]([a-z_][a-z0-9_]*)['\"]",
        re.IGNORECASE,
    )
    return {(a or b).lower() for a, b in pattern.findall(source)}


def _module_source(number: int) -> str:
    package = ROOT / "crypto_platform"
    main = package / ("platform.py" if number == 1 else f"module{number}.py")
    return main.read_text(encoding="utf-8")


def test_no_daily_module_or_delivery_code_reads_a_research_only_table() -> None:
    """Static guard: tables written only by weekly modules are not read on the daily path."""
    weekly_tables: set[str] = set()
    for number in EXPECTED_WEEKLY:
        weekly_tables |= _written_tables(_module_source(number))
    daily_sources = {number: _module_source(number) for number in UIP_DELIVERY_MODULES}
    daily_tables: set[str] = set()
    for source in daily_sources.values():
        daily_tables |= _written_tables(source)
    research_only_tables = weekly_tables - daily_tables
    # Checked by hand: "expected_returns" is a Python variable name in module 37, not a
    # table read. external_feature_observations is written by module 17 itself.
    allowed = {"expected_returns"}

    consumers = dict(daily_sources)
    consumers["module39_validation"] = (ROOT / "crypto_platform" / "module39_validation.py").read_text()
    for path in sorted((ROOT / "crypto_platform" / "ml").glob("*.py")):
        consumers[f"ml/{path.name}"] = path.read_text(encoding="utf-8")
    for path in sorted((ROOT / "crypto_platform" / "integration" / "universal").glob("*.py")):
        consumers[f"universal/{path.name}"] = path.read_text(encoding="utf-8")
    consumers["hosted.py"] = (ROOT / "crypto_platform" / "production" / "hosted.py").read_text()
    consumers["track_crypto_forecasts.py"] = (ROOT / "scripts" / "track_crypto_forecasts.py").read_text()

    found = []
    for name, source in consumers.items():
        for table in research_only_tables - allowed:
            if re.search(rf"\b{re.escape(table)}\b", source):
                found.append(f"{name} references {table}")
    assert found == []


def test_module17_ignores_the_external_rows_module18_adds() -> None:
    """Module 18 adds STABLECOIN_SUPPLY_USD rows to external_feature_observations; module 17
    reads only its own two keys from that table, so module 18 can run weekly."""
    module17 = (ROOT / "crypto_platform" / "module17.py").read_text(encoding="utf-8")
    module18 = (ROOT / "crypto_platform" / "module18.py").read_text(encoding="utf-8")
    assert re.findall(r"'feature_key':'([A-Z_]+)'", module18) == ["STABLECOIN_SUPPLY_USD"]
    assert set(re.findall(r'ext\.get\(\s*"([A-Z_]+)"', module17)) == {
        "FEAR_GREED_INDEX",
        "US_SPOT_CRYPTO_ETF_NET_FLOW_USD",
    }
    assert "STABLECOIN_SUPPLY_USD" not in module17


# --- orchestrator ------------------------------------------------------------------------


@pytest.fixture()
def stub_repo(tmp_path: Path, monkeypatch) -> dict:
    root = tmp_path / "repo"
    root.mkdir()
    for spec in active_modules():
        (root / spec.runner).write_text(STUB_RUNNER, encoding="utf-8")
    log = tmp_path / "ran.log"
    monkeypatch.setenv("STUB_RUN_LOG", str(log))
    monkeypatch.delenv("STUB_FAIL_MODULES", raising=False)
    monkeypatch.delenv("CRYPTO_PRODUCTION_RUN_ID", raising=False)
    database = tmp_path / "crypto.duckdb"
    return {"root": root, "log": log, "database": database, "output": tmp_path / "runs"}


def _record_runs(database: Path, ages_days: dict[int, float | None], *, status: str = "SUCCESS") -> None:
    connection = duckdb.connect(str(database))
    now = datetime.now(timezone.utc)
    try:
        for number, age in ages_days.items():
            spec = next(item for item in MODULE_REGISTRY if item.number == number)
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS {spec.run_table}("
                "run_id VARCHAR, started_at_utc TIMESTAMPTZ, completed_at_utc TIMESTAMPTZ, status VARCHAR)"
            )
            if age is not None:
                completed = now - timedelta(days=age)
                connection.execute(
                    f"INSERT INTO {spec.run_table} VALUES (?, ?, ?, ?)",
                    [f"run-{number}", completed - timedelta(minutes=1), completed, status],
                )
    finally:
        connection.close()


def _run(stub_repo: dict, **options):
    summary = ProductionOrchestrator(
        PipelineOptions(
            repository_root=stub_repo["root"],
            output_root=stub_repo["output"],
            export_universal=False,
            source_database=stub_repo["database"],
            **options,
        )
    ).run()
    log = stub_repo["log"]
    ran = [int(line) for line in log.read_text().split()] if log.exists() else []
    return summary, ran


def test_recent_research_modules_are_skipped_weekly(stub_repo) -> None:
    _record_runs(stub_repo["database"], {number: 1.0 for number in EXPECTED_WEEKLY})
    summary, ran = _run(stub_repo, weekly_research=True)

    assert summary.status == "PASS"
    assert summary.weekly_research is True
    assert ran == list(UIP_DELIVERY_MODULES)
    by_module = {item["module"]: item for item in summary.module_results}
    assert len(by_module) == 43
    for number in EXPECTED_WEEKLY:
        item = by_module[number]
        assert item["status"] == SKIPPED_WEEKLY
        assert item["duration_seconds"] == 0.0
        assert item["last_success_at_utc"].endswith("Z")
        assert 0.9 < item["last_success_age_days"] < 1.1
    for number in UIP_DELIVERY_MODULES:
        assert by_module[number]["status"] == "PASS"
    written = json.loads(Path(summary.run_directory, "run_summary.json").read_text())
    assert written["status"] == "PASS"
    assert sum(item["status"] == SKIPPED_WEEKLY for item in written["module_results"]) == 23


def test_stale_missing_or_never_successful_research_modules_run(stub_repo) -> None:
    ages = {number: 2.0 for number in EXPECTED_WEEKLY}
    ages[24] = 7.5  # last success over 7 days ago
    del ages[10]  # no run table at all
    ages[12] = None  # run table exists but is empty
    del ages[13]
    _record_runs(stub_repo["database"], ages)
    _record_runs(stub_repo["database"], {13: 0.5}, status="FAILED")  # never succeeded

    summary, ran = _run(stub_repo, weekly_research=True)

    assert summary.status == "PASS"
    assert sorted(ran) == sorted([*UIP_DELIVERY_MODULES, 10, 12, 13, 24])
    statuses = {item["module"]: item["status"] for item in summary.module_results}
    assert statuses[24] == statuses[10] == statuses[12] == statuses[13] == "PASS"
    assert statuses[2] == SKIPPED_WEEKLY


def test_missing_database_runs_every_module(stub_repo) -> None:
    summary, ran = _run(stub_repo, weekly_research=True)
    assert summary.status == "PASS"
    assert sorted(ran) == sorted(spec.number for spec in active_modules())


def test_full_refresh_runs_every_module(stub_repo) -> None:
    _record_runs(stub_repo["database"], {number: 1.0 for number in EXPECTED_WEEKLY})
    summary, ran = _run(stub_repo, weekly_research=True, full_refresh=True)
    assert summary.status == "PASS"
    assert ran == [spec.number for spec in active_modules()]
    assert all(item["status"] == "PASS" for item in summary.module_results)


def test_without_the_option_every_module_runs(stub_repo) -> None:
    _record_runs(stub_repo["database"], {number: 1.0 for number in EXPECTED_WEEKLY})
    summary, ran = _run(stub_repo)
    assert summary.weekly_research is False
    assert ran == [spec.number for spec in active_modules()]


def test_required_module_failure_still_fails_closed(stub_repo, monkeypatch) -> None:
    _record_runs(stub_repo["database"], {number: 1.0 for number in EXPECTED_WEEKLY})
    monkeypatch.setenv("STUB_FAIL_MODULES", "39")
    summary, ran = _run(stub_repo, weekly_research=True)
    assert summary.status == "FAIL"
    assert ran[-1] == 39 and 40 not in ran
    assert summary.module_results[-1]["module"] == 39
    assert summary.module_results[-1]["status"] == "FAIL"


def test_due_research_module_failure_still_fails_the_run(stub_repo, monkeypatch) -> None:
    ages = {number: 1.0 for number in EXPECTED_WEEKLY}
    ages[24] = 9.0
    _record_runs(stub_repo["database"], ages)
    monkeypatch.setenv("STUB_FAIL_MODULES", "24")
    summary, ran = _run(stub_repo, weekly_research=True)
    assert summary.status == "FAIL"
    assert ran[-1] == 24


# --- delivery and readiness ---------------------------------------------------------------


def test_uip_delivery_accepts_a_run_with_skipped_research_modules(stub_repo, tmp_path) -> None:
    _record_runs(stub_repo["database"], {number: 1.0 for number in EXPECTED_WEEKLY})
    summary, _ = _run(stub_repo, weekly_research=True)
    package = tmp_path / "package"
    package.mkdir()
    for name in (
        "asset_master.csv", "forecasts.csv", "platform_status.csv",
        "portfolio_positions.csv", "recommendations.csv", "risk_metrics.csv",
        "export_manifest.csv", "package_summary.json", "validation_report.json",
    ):
        (package / name).write_text("x\n", encoding="utf-8")
    payload = json.loads(Path(summary.run_directory, "run_summary.json").read_text())
    payload["universal_export"] = {"status": "PASS", "output_directory": str(package)}
    summary_path = Path(summary.run_directory, "run_summary.json")
    summary_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest = prepare_uip_delivery(summary_path, tmp_path / "delivery")
    assert manifest["status"] == "PASS"


def test_hosted_readiness_does_not_need_research_modules(tmp_path) -> None:
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    _record_runs(database, {24: 30.0, 10: None})
    assert evaluate_hosted_database(database)["status"] == "PASS"


def test_strict_production_readiness_check_passes() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_crypto_production_readiness.py"), "--strict"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


# --- workflow -----------------------------------------------------------------------------


def test_workflow_uses_weekly_research_and_sunday_full_refresh_runs_everything() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'EXTRA_ARGS="$EXTRA_ARGS --weekly-research"' in text
    assert 'if [[ "$CRYPTO_ALL_MODULES_REQUESTED" != "true" ]]; then' in text
    # The Sunday schedule still passes --full-refresh, which runs every module.
    assert "github.event.schedule == '45 10 * * 0'" in text
    assert 'EXTRA_ARGS="--full-refresh"' in text
    assert "python -m pytest tests/production -q" in text


def test_report_the_slowest_modules_step_handles_skipped_modules(tmp_path, monkeypatch) -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "- name: Report the slowest modules" in text
    step = text.split("- name: Report the slowest modules", 1)[1]
    script = textwrap.dedent(step.split("python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0])
    run_id = "gha-test-1"
    summary_dir = tmp_path / "data/operations/crypto/production_runs" / run_id
    summary_dir.mkdir(parents=True)
    (summary_dir / "run_summary.json").write_text(json.dumps({"module_results": [
        {"module": 39, "status": "PASS", "duration_seconds": 400.0},
        {"module": 24, "status": SKIPPED_WEEKLY, "duration_seconds": 0.0},
        {"module": 10, "status": SKIPPED_WEEKLY, "duration_seconds": 0.0},
        {"module": 2, "status": "RESUMED_PASS"},
    ]}))
    monkeypatch.setenv("CRYPTO_PRODUCTION_RUN_ID", run_id)
    completed = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, capture_output=True, text=True, check=False,
        env={"CRYPTO_PRODUCTION_RUN_ID": run_id, "PATH": "/usr/bin:/bin"},
    )
    assert completed.returncode == 0, completed.stderr
    assert "::notice title=Crypto module timings (6.7 min in modules)::module 39: 6.7 min (PASS)" in completed.stdout
    assert "skipped (weekly research): 10, 24" in completed.stdout
