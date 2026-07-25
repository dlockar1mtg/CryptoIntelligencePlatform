from __future__ import annotations

from dataclasses import asdict, dataclass
import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "observation_date",
    "strategy_return",
    "benchmark_return",
    "prediction_correct",
    "predicted_probability",
    "actual_probability",
    "market_regime",
}


@dataclass(frozen=True)
class PerformanceWindowMetrics:
    observations: int
    directional_accuracy_pct: float
    brier_score: float
    calibration_error: float
    cumulative_return_pct: float
    benchmark_return_pct: float
    excess_return_pct: float
    maximum_drawdown_pct: float
    annualized_sharpe: float
    decision_hit_rate_pct: float


@dataclass(frozen=True)
class PerformanceDriftResult:
    reference: PerformanceWindowMetrics
    current: PerformanceWindowMetrics
    accuracy_change_pct_points: float
    brier_change: float
    calibration_error_change: float
    excess_return_change_pct_points: float
    drawdown_change_pct_points: float
    sharpe_change: float
    hit_rate_change_pct_points: float
    breached_metrics: tuple[str, ...]
    drift_score: float
    drift_status: str
    governance_action: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["breached_metrics"] = list(self.breached_metrics)
        return result


@dataclass(frozen=True)
class PerformanceDriftThresholds:
    minimum_observations: int = 30
    warning_accuracy_drop_pct_points: float = 5.0
    critical_accuracy_drop_pct_points: float = 10.0
    warning_brier_increase: float = 0.03
    critical_brier_increase: float = 0.07
    warning_calibration_increase: float = 0.03
    critical_calibration_increase: float = 0.07
    warning_excess_return_drop_pct_points: float = 3.0
    critical_excess_return_drop_pct_points: float = 7.5
    warning_drawdown_worsening_pct_points: float = 5.0
    critical_drawdown_worsening_pct_points: float = 10.0
    warning_sharpe_drop: float = 0.40
    critical_sharpe_drop: float = 0.80
    warning_hit_rate_drop_pct_points: float = 5.0
    critical_hit_rate_drop_pct_points: float = 10.0
    warning_breach_count: int = 2
    retrain_breach_count: int = 3
    rollback_breach_count: int = 5


def _validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))

    if missing:
        raise ValueError(
            "Performance data is missing required columns: "
            + ", ".join(missing)
        )

    if frame.empty:
        raise ValueError("Performance data cannot be empty.")

    result = frame.copy()
    result["observation_date"] = pd.to_datetime(
        result["observation_date"],
        errors="raise",
    )
    result = result.sort_values("observation_date")

    numeric_columns = [
        "strategy_return",
        "benchmark_return",
        "prediction_correct",
        "predicted_probability",
        "actual_probability",
    ]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="raise",
        )

    if not result["prediction_correct"].between(0, 1).all():
        raise ValueError(
            "prediction_correct must contain values between 0 and 1."
        )

    if not result["predicted_probability"].between(0, 1).all():
        raise ValueError(
            "predicted_probability must contain values between 0 and 1."
        )

    if not result["actual_probability"].between(0, 1).all():
        raise ValueError(
            "actual_probability must contain values between 0 and 1."
        )

    return result


def _cumulative_return(returns: pd.Series) -> float:
    return float((1.0 + returns).prod() - 1.0)


def _maximum_drawdown(returns: pd.Series) -> float:
    cumulative = (1.0 + returns).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1.0
    return float(drawdown.min())


def _annualized_sharpe(returns: pd.Series) -> float:
    standard_deviation = float(returns.std(ddof=1))

    if not np.isfinite(standard_deviation) or standard_deviation <= 0:
        return 0.0

    return float(
        returns.mean()
        / standard_deviation
        * np.sqrt(365.0)
    )


def calculate_window_metrics(
    frame: pd.DataFrame,
) -> PerformanceWindowMetrics:
    data = _validate_frame(frame)

    strategy_return = data["strategy_return"]
    benchmark_return = data["benchmark_return"]

    cumulative_return = _cumulative_return(strategy_return)
    benchmark_cumulative_return = _cumulative_return(
        benchmark_return
    )

    brier = float(
        np.mean(
            (
                data["predicted_probability"]
                - data["actual_probability"]
            )
            ** 2
        )
    )

    calibration_error = float(
        abs(
            data["predicted_probability"].mean()
            - data["actual_probability"].mean()
        )
    )

    return PerformanceWindowMetrics(
        observations=len(data),
        directional_accuracy_pct=float(
            data["prediction_correct"].mean() * 100.0
        ),
        brier_score=brier,
        calibration_error=calibration_error,
        cumulative_return_pct=cumulative_return * 100.0,
        benchmark_return_pct=(
            benchmark_cumulative_return * 100.0
        ),
        excess_return_pct=(
            cumulative_return - benchmark_cumulative_return
        )
        * 100.0,
        maximum_drawdown_pct=(
            _maximum_drawdown(strategy_return) * 100.0
        ),
        annualized_sharpe=_annualized_sharpe(strategy_return),
        decision_hit_rate_pct=float(
            (
                (
                    data["strategy_return"]
                    - data["benchmark_return"]
                )
                > 0
            ).mean()
            * 100.0
        ),
    )


def _severity(
    value: float,
    *,
    warning: float,
    critical: float,
) -> int:
    if value >= critical:
        return 2

    if value >= warning:
        return 1

    return 0


def evaluate_performance_drift(
    reference_frame: pd.DataFrame,
    current_frame: pd.DataFrame,
    thresholds: PerformanceDriftThresholds | None = None,
) -> PerformanceDriftResult:
    limits = thresholds or PerformanceDriftThresholds()

    reference = calculate_window_metrics(reference_frame)
    current = calculate_window_metrics(current_frame)

    if reference.observations < limits.minimum_observations:
        raise ValueError(
            "Reference window does not meet the minimum observation "
            f"requirement of {limits.minimum_observations}."
        )

    if current.observations < limits.minimum_observations:
        raise ValueError(
            "Current window does not meet the minimum observation "
            f"requirement of {limits.minimum_observations}."
        )

    changes = {
        "directional_accuracy": (
            reference.directional_accuracy_pct
            - current.directional_accuracy_pct
        ),
        "brier_score": (
            current.brier_score
            - reference.brier_score
        ),
        "calibration_error": (
            current.calibration_error
            - reference.calibration_error
        ),
        "excess_return": (
            reference.excess_return_pct
            - current.excess_return_pct
        ),
        "maximum_drawdown": max(
            0.0,
            abs(current.maximum_drawdown_pct)
            - abs(reference.maximum_drawdown_pct),
        ),
        "annualized_sharpe": (
            reference.annualized_sharpe
            - current.annualized_sharpe
        ),
        "decision_hit_rate": (
            reference.decision_hit_rate_pct
            - current.decision_hit_rate_pct
        ),
    }

    severity = {
        "directional_accuracy": _severity(
            changes["directional_accuracy"],
            warning=limits.warning_accuracy_drop_pct_points,
            critical=limits.critical_accuracy_drop_pct_points,
        ),
        "brier_score": _severity(
            changes["brier_score"],
            warning=limits.warning_brier_increase,
            critical=limits.critical_brier_increase,
        ),
        "calibration_error": _severity(
            changes["calibration_error"],
            warning=limits.warning_calibration_increase,
            critical=limits.critical_calibration_increase,
        ),
        "excess_return": _severity(
            changes["excess_return"],
            warning=limits.warning_excess_return_drop_pct_points,
            critical=limits.critical_excess_return_drop_pct_points,
        ),
        "maximum_drawdown": _severity(
            changes["maximum_drawdown"],
            warning=limits.warning_drawdown_worsening_pct_points,
            critical=limits.critical_drawdown_worsening_pct_points,
        ),
        "annualized_sharpe": _severity(
            changes["annualized_sharpe"],
            warning=limits.warning_sharpe_drop,
            critical=limits.critical_sharpe_drop,
        ),
        "decision_hit_rate": _severity(
            changes["decision_hit_rate"],
            warning=limits.warning_hit_rate_drop_pct_points,
            critical=limits.critical_hit_rate_drop_pct_points,
        ),
    }

    breached = tuple(
        metric
        for metric, metric_severity in severity.items()
        if metric_severity > 0
    )

    critical_count = sum(
        metric_severity == 2
        for metric_severity in severity.values()
    )
    breach_count = len(breached)
    drift_score = float(sum(severity.values()))

    if (
        breach_count >= limits.rollback_breach_count
        or critical_count >= 3
    ):
        drift_status = "CRITICAL"
        governance_action = "ROLLBACK"
    elif (
        breach_count >= limits.retrain_breach_count
        or critical_count >= 1
    ):
        drift_status = "DEGRADED"
        governance_action = "RETRAIN"
    elif breach_count >= limits.warning_breach_count:
        drift_status = "WARNING"
        governance_action = "MONITOR"
    else:
        drift_status = "HEALTHY"
        governance_action = "NONE"

    return PerformanceDriftResult(
        reference=reference,
        current=current,
        accuracy_change_pct_points=-changes[
            "directional_accuracy"
        ],
        brier_change=changes["brier_score"],
        calibration_error_change=changes["calibration_error"],
        excess_return_change_pct_points=-changes[
            "excess_return"
        ],
        drawdown_change_pct_points=-changes[
            "maximum_drawdown"
        ],
        sharpe_change=-changes["annualized_sharpe"],
        hit_rate_change_pct_points=-changes[
            "decision_hit_rate"
        ],
        breached_metrics=breached,
        drift_score=drift_score,
        drift_status=drift_status,
        governance_action=governance_action,
    )


def performance_by_regime(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    data = _validate_frame(frame)
    rows: list[dict[str, object]] = []

    for regime, group in data.groupby(
        "market_regime",
        sort=True,
    ):
        metrics = calculate_window_metrics(group)
        row = {
            "market_regime": str(regime),
            **asdict(metrics),
        }
        rows.append(row)

    return pd.DataFrame(rows)