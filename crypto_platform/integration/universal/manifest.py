"""Universal export-manifest generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path

from .context import ExportContext


EXPORT_MANIFEST_COLUMNS = [
    "contract_version",
    "platform_id",
    "run_id",
    "dataset_name",
    "file_name",
    "record_count",
    "file_size_bytes",
    "sha256",
    "schema_version",
    "generated_at_utc",
    "validation_status",
]


@dataclass(frozen=True)
class UniversalManifestRecord:
    contract_version: str
    platform_id: str
    run_id: str
    dataset_name: str
    file_name: str
    record_count: int
    file_size_bytes: int
    sha256: str
    schema_version: str
    generated_at_utc: str
    validation_status: str

    def to_dict(
        self,
    ) -> dict[str, object]:
        return asdict(self)


def calculate_sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def build_manifest_record(
    *,
    context: ExportContext,
    dataset_name: str,
    file_path: Path,
    record_count: int,
    validation_status: str = "PASS",
) -> UniversalManifestRecord:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Manifest file does not exist: {file_path}"
        )

    return UniversalManifestRecord(
        contract_version=context.contract_version,
        platform_id=context.platform_id,
        run_id=context.run_id,
        dataset_name=dataset_name,
        file_name=file_path.name,
        record_count=record_count,
        file_size_bytes=file_path.stat().st_size,
        sha256=calculate_sha256(file_path),
        schema_version=context.contract_version,
        generated_at_utc=context.generated_at_iso,
        validation_status=validation_status,
    )