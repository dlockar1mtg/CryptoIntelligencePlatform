from __future__ import annotations
from crypto_platform.module2 import clamp

def composite_objective(metrics: dict) -> float:
    ir = metrics.get("information_ratio")
    ir_score = clamp((((ir if ir is not None else -1.0) + 1.0) / 3.0) * 100)
    return_score = clamp(((metrics.get("annualized_return", -0.25) + 0.25) / 1.0) * 100)
    drawdown_score = clamp(((metrics.get("maximum_drawdown", -0.80) + 0.80) / 0.80) * 100)
    win_score = clamp(metrics.get("benchmark_win_rate", 0.0))
    turnover_score = clamp(((0.50 - metrics.get("average_turnover", 0.50)) / 0.50) * 100)
    return float(
        return_score * 0.30 + ir_score * 0.25 + drawdown_score * 0.20
        + win_score * 0.15 + turnover_score * 0.10
    )
