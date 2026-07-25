# Phase 9.2 — Hosted Operations and UIP Delivery

## Purpose

Phase 9.2 makes the governed Phase 9.1 pipeline durable on GitHub-hosted runners without granting the Crypto repository write access to UIP.

## Controls added

- DuckDB state is restored from the most recent compatible GitHub Actions cache.
- A successful run saves a new immutable cache key.
- The production run ID is tied to the GitHub run and attempt.
- Hosted readiness verifies database presence, required tables, latest collection success, provider health, market freshness, and macro freshness.
- A validated universal package is copied into a stable delivery directory.
- Every delivered file receives a SHA-256 checksum in `uip_delivery_manifest.json`.
- Run summaries, readiness evidence, and the UIP delivery package are uploaded as one retained workflow artifact.
- Scheduled execution remains disabled until hosted certification is complete.

## Trust boundary

Crypto publishes an artifact. It does not push commits to UIP and does not receive a UIP repository token. UIP ingestion will authenticate separately and consume only a checksum-verified package.

## Default freshness standards

- Latest collection run: no more than 72 hours old
- Daily market observation: no more than 72 hours old
- Latest macro observation: no more than 60 days old
- Failed collectors: zero
- Latest provider states: online/available/healthy/pass

## Local validation

```powershell
python -m pytest tests\production -q
python scripts\check_crypto_production_readiness.py --strict
python scripts\check_crypto_hosted_readiness.py --strict
```

## Hosted certification sequence

1. Dispatch the workflow manually.
2. Confirm the pipeline passes.
3. Confirm a database cache is created.
4. Confirm `hosted_readiness.json` is PASS.
5. Download the production artifact.
6. Verify the UIP delivery manifest and package checksums.
7. Dispatch a second run and confirm the database cache is restored.
8. Only then consider adding a schedule.
