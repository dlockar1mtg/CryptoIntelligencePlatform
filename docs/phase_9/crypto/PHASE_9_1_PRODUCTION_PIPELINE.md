# Phase 9.1 — Governed Crypto Production Pipeline

## Decision

The existing 43 implemented modules remain intact. Production orchestration is added above their tested runners instead of rewriting model code.

Module 4 is formally retired because no implementation or runner exists. The numbering gap is retained for historical compatibility and cannot silently become a dependency.

## Authoritative execution stages

1. Collection — Module 1
2. Core analytics — Modules 2–16, excluding retired Module 4
3. Feature research — Modules 17–24
4. Regime validation — Modules 25–32
5. Decision intelligence — Modules 33–42
6. Governance — Modules 43–44
7. Universal export — read-only package builder sourced from successful Module 36, 39, and 42 runs

## Operational controls

- dependency-ordered module execution;
- stop on required-module failure;
- optional-module failure policy;
- one production run identifier;
- separate stdout and stderr logs per module;
- atomic machine-readable run summary;
- bounded module and stage execution;
- resume-aware summaries;
- explicit universal package validation;
- GitHub Actions scheduling and manual dispatch;
- no live trading or order execution.

## Commands

Static readiness:

```powershell
python scripts\check_crypto_production_readiness.py --strict
```

Focused dry execution without export:

```powershell
python scripts\run_crypto_production_pipeline.py --start-module 1 --end-module 2 --no-export
```

Full production cycle:

```powershell
python scripts\run_crypto_production_pipeline.py
```

## Certification boundary

Phase 9.1 certifies orchestration structure. It does not yet certify sustained provider availability, forward prediction performance, exchange reconciliation, live holdings accounting, or unattended trading.
