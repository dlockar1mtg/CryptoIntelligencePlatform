"""Universal Investment Platform export adapter for crypto data."""

ADAPTER_VERSION = "1.1.0"
CONTRACT_VERSION = "1.0.0"
PLATFORM_ID = "crypto"
PLATFORM_NAME = "Crypto Intelligence Platform"

from .analytics_repository import (
    CryptoAnalyticsRepository,
)
from .asset_master import (
    ASSET_MASTER_COLUMNS,
    UniversalAssetRecord,
    build_asset_master,
    transform_asset,
)
from .btc_eth_strategic_overlay import (
    BTC_ETH_STRATEGIC_OVERLAY_COLUMNS,
    BtcEthStrategicOverlayRecord,
    build_btc_eth_strategic_overlay,
)
from .context import ExportContext
from .forecasts import (
    FORECAST_COLUMNS,
    UniversalForecastRecord,
    build_forecasts,
    transform_calibrated_forecast,
    transform_price_projection,
)
from .manifest import (
    EXPORT_MANIFEST_COLUMNS,
    UniversalManifestRecord,
)
from .package_builder import (
    PackageBuildResult,
    UniversalPackageBuilder,
)
from .platform_status import (
    PLATFORM_STATUS_COLUMNS,
    UniversalPlatformStatusRecord,
    build_platform_status,
)
from .portfolio_positions import (
    PORTFOLIO_POSITION_COLUMNS,
    UniversalPortfolioPositionRecord,
    build_empty_portfolio_positions,
)
from .recommendations import (
    RECOMMENDATION_COLUMNS,
    UniversalRecommendationRecord,
    build_recommendations,
    transform_recommendation,
)
from .risk_metrics import (
    RISK_METRIC_COLUMNS,
    UniversalRiskMetricRecord,
    build_risk_metrics,
    transform_risk_metric,
)
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
    "BTC_ETH_STRATEGIC_OVERLAY_COLUMNS",
    "BtcEthStrategicOverlayRecord",
    "CONTRACT_VERSION",
    "CryptoAnalyticsRepository",
    "CryptoSourceRepository",
    "EXPORT_MANIFEST_COLUMNS",
    "ExportContext",
    "FORECAST_COLUMNS",
    "PLATFORM_ID",
    "PLATFORM_NAME",
    "PLATFORM_STATUS_COLUMNS",
    "PORTFOLIO_POSITION_COLUMNS",
    "PackageBuildResult",
    "RECOMMENDATION_COLUMNS",
    "RISK_METRIC_COLUMNS",
    "SourceAsset",
    "SourceRun",
    "UniversalAssetRecord",
    "UniversalForecastRecord",
    "UniversalManifestRecord",
    "UniversalPackageBuilder",
    "UniversalPlatformStatusRecord",
    "UniversalPortfolioPositionRecord",
    "UniversalRecommendationRecord",
    "UniversalRiskMetricRecord",
    "build_asset_master",
    "build_btc_eth_strategic_overlay",
    "build_empty_portfolio_positions",
    "build_forecasts",
    "build_platform_status",
    "build_recommendations",
    "build_risk_metrics",
    "transform_asset",
    "transform_calibrated_forecast",
    "transform_price_projection",
    "transform_recommendation",
    "transform_risk_metric",
]
