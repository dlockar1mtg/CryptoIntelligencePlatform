"""Universal Investment Platform export adapter for crypto data."""

ADAPTER_VERSION = "1.0.0"
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
from .context import ExportContext
from .forecasts import (
    FORECAST_COLUMNS,
    UniversalForecastRecord,
    build_forecasts,
    transform_calibrated_forecast,
    transform_price_projection,
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
    "CONTRACT_VERSION",
    "CryptoAnalyticsRepository",
    "CryptoSourceRepository",
    "ExportContext",
    "FORECAST_COLUMNS",
    "PLATFORM_ID",
    "PLATFORM_NAME",
    "RECOMMENDATION_COLUMNS",
    "RISK_METRIC_COLUMNS",
    "SourceAsset",
    "SourceRun",
    "UniversalAssetRecord",
    "UniversalForecastRecord",
    "UniversalRecommendationRecord",
    "UniversalRiskMetricRecord",
    "build_asset_master",
    "build_forecasts",
    "build_recommendations",
    "build_risk_metrics",
    "transform_asset",
    "transform_calibrated_forecast",
    "transform_price_projection",
    "transform_recommendation",
    "transform_risk_metric",
]