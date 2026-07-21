# UIP Package Identity Compatibility

## Status

The Crypto Universal Export Adapter produces Universal Investment Platform
contract version `1.0.0` datasets that pass the authoritative UIP CSV and JSON
Schema validators.

The generated package also passes UIP package discovery, checksum validation,
file-size validation, and row-count validation.

## Confirmed Identity Limitation

The UIP `platform_status.csv` contract does not contain an
`adapter_version` column.

The current UIP package parser attempts to establish `adapter_version` only
from `platform_status.csv`.

As a result, the parser currently discovers the package with an empty adapter
version value.

This is a UIP parser limitation rather than a crypto export contract failure.

## Crypto Adapter Behavior

The crypto adapter preserves the adapter version in:

- `package_summary.json`
- the platform-status message
- the adapter source-code constant
- the generated package context

The crypto adapter does not add a noncontract `adapter_version` column to
`platform_status.csv`.

## Required UIP Follow-Up

The UIP package parser should establish adapter version using a deterministic
fallback, such as:

1. authoritative package metadata;
2. export-manifest package identity fields;
3. `package_summary.json`;
4. platform registry compatibility metadata.

The UIP correction should preserve backward compatibility with existing
packages.

## Certification State

- Asset master contract: PASS
- Forecasts contract: PASS
- Platform status contract: PASS
- Header-only portfolio positions contract: PASS
- Recommendations contract: PASS
- Risk metrics contract: PASS
- UIP discovery and integrity validation: PASS
- Crypto adapter test suite: PASS
- Complete crypto repository test suite: PASS
