"""Universal Investment Platform export adapter for crypto data."""

ADAPTER_VERSION = "1.0.0"
CONTRACT_VERSION = "1.0.0"
PLATFORM_ID = "crypto"
PLATFORM_NAME = "Crypto Intelligence Platform"

from .asset_master import (
    ASSET_MASTER_COLUMNS,
    UniversalAssetRecord,
    build_asset_master,
    transform_asset,
)
from .context import ExportContext
from .source_models import (
    SourceAsset,
    SourceRun,
)
from .source_repository import (
    CryptoSourceRepository,
)

__all__ = [
    "ADAPTER_VERSION",
    "ASSET_MASTER_COLUMNS",
    "CONTRACT_VERSION",
    "CryptoSourceRepository",
    "ExportContext",
    "PLATFORM_ID",
    "PLATFORM_NAME",
    "SourceAsset",
    "SourceRun",
    "UniversalAssetRecord",
    "build_asset_master",
    "transform_asset",
]