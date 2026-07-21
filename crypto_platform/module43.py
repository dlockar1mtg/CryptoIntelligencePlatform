from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from crypto_platform.platform import load_all, connect
from crypto_platform.module42 import MODULE42_SCHEMA


MODULE43_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module43_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module42_run_id VARCHAR,
    prior_module42_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    ranked_assets INTEGER,
    change_rows INTEGER,
    trigger_rows INTEGER,
    thesis_rows INTEGER,
    timing_rows INTEGER,
    committee_rows INTEGER,
    positive_actions INTEGER,
    material_changes INTEGER,
    evidence_status VARCHAR,
    committee_decision VARCHAR,
    recommendation VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m43_opportunity_ranking(
    run_id VARCHAR,
    recommendation_date DATE,
    opportunity_rank INTEGER,
    asset_id VARCHAR,
    investment_score DOUBLE,
    score_percentile DOUBLE,
    best_action VARCHAR,
    conviction_tier VARCHAR,
    target_portfolio_pct DOUBLE,
    current_portfolio_pct DOUBLE,
    forecast_confidence DOUBLE,
    reliability_score DOUBLE,
    short_term_signal DOUBLE,
    medium_term_signal DOUBLE,
    long_term_signal DOUBLE,
    relative_opportunity_score DOUBLE,
    opportunity_status VARCHAR,
    primary_reason VARCHAR,
    evidence_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS m43_decision_changes(
    run_id VARCHAR,
    asset_id VARCHAR,
    current_recommendation_date DATE,
    prior_recommendation_date DATE,
    current_action VARCHAR,
    prior_action VARCHAR,
    action_changed BOOLEAN,
    score_change DOUBLE,
    target_weight_change_pct DOUBLE,
    confidence_change DOUBLE,
    reliability_change DOUBLE,
    median_30d_price_change_pct DOUBLE,
    median_3m_price_change_pct DOUBLE,
    change_magnitude_score DOUBLE,
    change_classification VARCHAR,
    change_summary VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS m43_action_triggers(
    run_id VARCHAR,
    asset_id VARCHAR,
    current_action VARCHAR,
    upgrade_action VARCHAR,
    upgrade_score_required DOUBLE,
    upgrade_confidence_required DOUBLE,
    upgrade_30d_return_required DOUBLE,
    upgrade_3m_return_required DOUBLE,
    upgrade_condition VARCHAR,
    downgrade_action VARCHAR,
    downgrade_score_threshold DOUBLE,
    downgrade_30d_return_threshold DOUBLE,
    downgrade_condition VARCHAR,
    current_distance_to_upgrade DOUBLE,
    trigger_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS m43_thesis_monitor(
    run_id VARCHAR,
    asset_id VARCHAR,
    thesis_summary VARCHAR,
    supporting_evidence VARCHAR,
    invalidation_condition VARCHAR,
    downside_risk VARCHAR,
    monitoring_priority VARCHAR,
    thesis_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS m43_buy_wait_analysis(
    run_id VARCHAR,
    asset_id VARCHAR,
    current_action VARCHAR,
    current_price DOUBLE,
    median_7d_price DOUBLE,
    median_30d_price DOUBLE,
    median_3m_price DOUBLE,
    buy_now_30d_return_pct DOUBLE,
    wait_7d_then_30d_return_pct DOUBLE,
    wait_30d_then_3m_return_pct DOUBLE,
    estimated_wait_advantage_pct DOUBLE,
    timing_preference VARCHAR,
    timing_confidence DOUBLE,
    timing_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS m43_committee_brief(
    run_id VARCHAR PRIMARY KEY,
    recommendation_date DATE,
    committee_decision VARCHAR,
    capital_posture VARCHAR,
    review_window VARCHAR,
    target_crypto_pct DOUBLE,
    target_cash_pct DOUBLE,
    highest_ranked_asset VARCHAR,
    highest_ranked_score DOUBLE,
    key_change VARCHAR,
    primary_risk VARCHAR,
    decision_rationale VARCHAR,
    conditions_to_deploy VARCHAR,
    conditions_to_reduce VARCHAR,
    evidence_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m43_opportunity_ranking AS
SELECT *
FROM m43_opportunity_ranking
WHERE run_id=(
    SELECT run_id
    FROM module43_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY opportunity_rank;

CREATE OR REPLACE VIEW latest_m43_decision_changes AS
SELECT *
FROM m43_decision_changes
WHERE run_id=(
    SELECT run_id
    FROM module43_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY change_magnitude_score DESC;

CREATE OR REPLACE VIEW latest_m43_action_triggers AS
SELECT *
FROM m43_action_triggers
WHERE run_id=(
    SELECT run_id
    FROM module43_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY current_distance_to_upgrade;

CREATE OR REPLACE VIEW latest_m43_thesis_monitor AS
SELECT *
FROM m43_thesis_monitor
WHERE run_id=(
    SELECT run_id
    FROM module43_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY
    CASE monitoring_priority
        WHEN 'HIGH' THEN 1
        WHEN 'MEDIUM' THEN 2
        ELSE 3
    END,
    asset_id;

CREATE OR REPLACE VIEW latest_m43_buy_wait_analysis AS
SELECT *
FROM m43_buy_wait_analysis
WHERE run_id=(
    SELECT run_id
    FROM module43_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
)
ORDER BY estimated_wait_advantage_pct DESC;

CREATE OR REPLACE VIEW latest_m43_committee_brief AS
SELECT *
FROM m43_committee_brief
WHERE run_id=(
    SELECT run_id
    FROM module43_runs
    ORDER BY started_at_utc DESC
    LIMIT 1
);
"""


def utcnow():
    return datetime.now(timezone.utc)


def safe_float(value, default=0.0):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def clip(value, lower, upper):
    return float(np.clip(value, lower, upper))


class Module43Runner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE42_SCHEMA)
        self.conn.execute(MODULE43_SCHEMA)
        self.cfg = self.settings["module43"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()

        runs = self.conn.execute(
            """
            SELECT run_id
            FROM module42_runs
            WHERE status='SUCCESS'
            ORDER BY started_at_utc DESC
            LIMIT 2
            """
        ).fetchall()
        if not runs:
            raise RuntimeError(
                "A successful Module 42 run is required."
            )
        self.source42 = str(runs[0][0])
        self.prior42 = (
            str(runs[1][0])
            if len(runs) > 1
            else None
        )

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m43_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"""
            INSERT OR REPLACE INTO {table}({columns})
            SELECT {columns}
            FROM _m43_stage
            """
        )
        self.conn.unregister("_m43_stage")

    def recommendations(self, run_id):
        return self.conn.execute(
            """
            SELECT *
            FROM m42_asset_recommendations
            WHERE run_id=?
            ORDER BY investment_score DESC
            """,
            [run_id],
        ).fetchdf()

    def projections(self, run_id):
        return self.conn.execute(
            """
            SELECT *
            FROM m42_price_projections
            WHERE run_id=?
            """,
            [run_id],
        ).fetchdf()

    def summary(self, run_id):
        row = self.conn.execute(
            """
            SELECT *
            FROM m42_decision_summary
            WHERE run_id=?
            """,
            [run_id],
        ).fetchdf()
        if row.empty:
            raise RuntimeError(
                "Module 42 decision summary is missing."
            )
        return row.iloc[0]

    def projection_value(
        self,
        frame,
        asset,
        label,
        column="median_price",
        default=np.nan,
    ):
        subset = frame[
            (frame["asset_id"] == asset)
            & (frame["horizon_label"] == label)
        ]
        if subset.empty:
            return default
        return safe_float(
            subset.iloc[0][column],
            default,
        )

    def conviction_tier(self, score):
        if score >= 90:
            return "EXCEPTIONAL"
        if score >= 80:
            return "VERY_HIGH"
        if score >= 70:
            return "HIGH"
        if score >= 60:
            return "MODERATE"
        if score >= 50:
            return "LOW"
        if score >= 40:
            return "VERY_LOW"
        return "NO_EDGE"

    def ranking(self, current):
        frame = current.copy()
        frame["relative_opportunity_score"] = (
            0.45 * frame["investment_score"].astype(float)
            + 0.20
            * frame["forecast_confidence"].astype(float)
            * 100
            + 0.15
            * frame["reliability_score"].astype(float)
            + 0.10
            * frame["medium_term_signal"].astype(float)
            + 0.10
            * frame["risk_score"].astype(float)
        )
        frame = frame.sort_values(
            [
                "relative_opportunity_score",
                "investment_score",
            ],
            ascending=False,
        ).reset_index(drop=True)
        rows = []
        count = len(frame)

        for index, row in frame.iterrows():
            score = safe_float(row["investment_score"])
            relative = safe_float(
                row["relative_opportunity_score"]
            )
            action = str(row["best_action"])
            if action in {
                "STRONG_BUY",
                "BUY",
                "SCALE_IN",
            }:
                status = "ACTIONABLE"
            elif action in {"HOLD", "WAIT"}:
                status = "WATCHLIST"
            else:
                status = "DEFENSIVE"

            rows.append({
                "run_id": self.run_id,
                "recommendation_date": row[
                    "recommendation_date"
                ],
                "opportunity_rank": index + 1,
                "asset_id": row["asset_id"],
                "investment_score": score,
                "score_percentile": (
                    100
                    if count == 1
                    else (
                        1
                        - index
                        / (count - 1)
                    )
                    * 100
                ),
                "best_action": action,
                "conviction_tier": (
                    self.conviction_tier(score)
                ),
                "target_portfolio_pct": safe_float(
                    row[
                        "best_current_portfolio_pct"
                    ]
                ),
                "current_portfolio_pct": (
                    safe_float(
                        row[
                            "current_portfolio_weight"
                        ]
                    )
                    * 100
                ),
                "forecast_confidence": safe_float(
                    row["forecast_confidence"]
                ),
                "reliability_score": safe_float(
                    row["reliability_score"]
                ),
                "short_term_signal": safe_float(
                    row["short_term_signal"]
                ),
                "medium_term_signal": safe_float(
                    row["medium_term_signal"]
                ),
                "long_term_signal": safe_float(
                    row["long_term_signal"]
                ),
                "relative_opportunity_score": (
                    relative
                ),
                "opportunity_status": status,
                "primary_reason": row[
                    "primary_reason"
                ],
                "evidence_status": row[
                    "evidence_status"
                ],
                "calculated_at_utc": utcnow(),
            })

        return pd.DataFrame(rows)

    def changes(
        self,
        current,
        current_projection,
        prior,
        prior_projection,
    ):
        rows = []
        current_date = current[
            "recommendation_date"
        ].max()
        prior_date = (
            prior["recommendation_date"].max()
            if not prior.empty
            else pd.NaT
        )

        for _, row in current.iterrows():
            asset = row["asset_id"]
            old = prior[
                prior["asset_id"] == asset
            ]
            if old.empty:
                prior_action = "NO_BASELINE"
                score_change = 0.0
                target_change = 0.0
                confidence_change = 0.0
                reliability_change = 0.0
                price30_change = 0.0
                price3m_change = 0.0
                action_changed = False
                classification = "BASELINE_CREATED"
                summary = (
                    "First institutional decision "
                    "snapshot for this asset."
                )
            else:
                old = old.iloc[0]
                prior_action = str(
                    old["best_action"]
                )
                score_change = (
                    safe_float(
                        row["investment_score"]
                    )
                    - safe_float(
                        old["investment_score"]
                    )
                )
                target_change = (
                    safe_float(
                        row[
                            "best_current_portfolio_pct"
                        ]
                    )
                    - safe_float(
                        old[
                            "best_current_portfolio_pct"
                        ]
                    )
                )
                confidence_change = (
                    safe_float(
                        row["forecast_confidence"]
                    )
                    - safe_float(
                        old["forecast_confidence"]
                    )
                )
                reliability_change = (
                    safe_float(
                        row["reliability_score"]
                    )
                    - safe_float(
                        old["reliability_score"]
                    )
                )
                current_30 = self.projection_value(
                    current_projection,
                    asset,
                    "30D",
                )
                old_30 = self.projection_value(
                    prior_projection,
                    asset,
                    "30D",
                )
                current_3m = self.projection_value(
                    current_projection,
                    asset,
                    "M03",
                )
                old_3m = self.projection_value(
                    prior_projection,
                    asset,
                    "M03",
                )
                price30_change = (
                    (
                        current_30 / old_30 - 1
                    )
                    * 100
                    if old_30
                    and np.isfinite(old_30)
                    else 0.0
                )
                price3m_change = (
                    (
                        current_3m / old_3m - 1
                    )
                    * 100
                    if old_3m
                    and np.isfinite(old_3m)
                    else 0.0
                )
                action_changed = (
                    str(row["best_action"])
                    != prior_action
                )
                magnitude = (
                    abs(score_change)
                    + abs(target_change) * 2
                    + abs(confidence_change) * 50
                    + abs(price30_change) * 0.25
                    + abs(price3m_change) * 0.20
                    + (15 if action_changed else 0)
                )
                classification = (
                    "MATERIAL_CHANGE"
                    if magnitude >= float(
                        self.cfg[
                            "material_change_threshold"
                        ]
                    )
                    else "MINOR_CHANGE"
                )
                summary = (
                    f"Action {prior_action} -> "
                    f"{row['best_action']}; "
                    f"score {score_change:+.1f}; "
                    f"target {target_change:+.2f}pp; "
                    f"30D median {price30_change:+.1f}%."
                )

            magnitude = (
                0.0
                if classification
                == "BASELINE_CREATED"
                else (
                    abs(score_change)
                    + abs(target_change) * 2
                    + abs(confidence_change) * 50
                    + abs(price30_change) * 0.25
                    + abs(price3m_change) * 0.20
                    + (15 if action_changed else 0)
                )
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": asset,
                "current_recommendation_date": (
                    current_date
                ),
                "prior_recommendation_date": (
                    prior_date
                ),
                "current_action": row[
                    "best_action"
                ],
                "prior_action": prior_action,
                "action_changed": action_changed,
                "score_change": score_change,
                "target_weight_change_pct": (
                    target_change
                ),
                "confidence_change": (
                    confidence_change
                ),
                "reliability_change": (
                    reliability_change
                ),
                "median_30d_price_change_pct": (
                    price30_change
                ),
                "median_3m_price_change_pct": (
                    price3m_change
                ),
                "change_magnitude_score": magnitude,
                "change_classification": (
                    classification
                ),
                "change_summary": summary,
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def triggers(self, current, projections):
        rows = []
        for _, row in current.iterrows():
            asset = row["asset_id"]
            score = safe_float(
                row["investment_score"]
            )
            confidence = safe_float(
                row["forecast_confidence"]
            )
            current_action = str(
                row["best_action"]
            )
            price = safe_float(
                row["current_price"]
            )
            price30 = self.projection_value(
                projections,
                asset,
                "30D",
            )
            price3m = self.projection_value(
                projections,
                asset,
                "M03",
            )
            return30 = (
                (price30 / price - 1) * 100
                if price
                else 0.0
            )
            return3m = (
                (price3m / price - 1) * 100
                if price
                else 0.0
            )

            if current_action in {
                "WAIT",
                "HOLD",
            }:
                upgrade_action = (
                    "SCALE_IN"
                )
                upgrade_score = float(
                    self.cfg[
                        "scale_in_score"
                    ]
                )
                upgrade_confidence = float(
                    self.cfg[
                        "minimum_upgrade_confidence"
                    ]
                )
                required_30 = float(
                    self.cfg[
                        "minimum_upgrade_30d_return"
                    ]
                )
                required_3m = float(
                    self.cfg[
                        "minimum_upgrade_3m_return"
                    ]
                )
            elif current_action == "SCALE_IN":
                upgrade_action = "BUY"
                upgrade_score = float(
                    self.cfg["buy_score"]
                )
                upgrade_confidence = float(
                    self.cfg[
                        "buy_confidence"
                    ]
                )
                required_30 = 2.0
                required_3m = 5.0
            elif current_action == "BUY":
                upgrade_action = "STRONG_BUY"
                upgrade_score = float(
                    self.cfg[
                        "strong_buy_score"
                    ]
                )
                upgrade_confidence = 0.70
                required_30 = 5.0
                required_3m = 10.0
            else:
                upgrade_action = "HOLD"
                upgrade_score = 45.0
                upgrade_confidence = 0.40
                required_30 = -2.0
                required_3m = 0.0

            distance = max(
                upgrade_score - score,
                0,
            )
            condition = (
                f"Score >= {upgrade_score:.0f}, "
                f"confidence >= "
                f"{upgrade_confidence:.0%}, "
                f"30D return >= {required_30:.1f}%, "
                f"3M return >= {required_3m:.1f}%."
            )
            downgrade_action = (
                "REDUCE"
                if current_action
                not in {"AVOID", "REDUCE"}
                else "AVOID"
            )
            downgrade_score = float(
                self.cfg[
                    "downgrade_score"
                ]
            )
            downgrade_return = float(
                self.cfg[
                    "downgrade_30d_return"
                ]
            )
            downgrade_condition = (
                f"Score < {downgrade_score:.0f} "
                f"or 30D return < "
                f"{downgrade_return:.1f}%."
            )
            trigger_status = (
                "UPGRADE_READY"
                if (
                    score >= upgrade_score
                    and confidence
                    >= upgrade_confidence
                    and return30 >= required_30
                    and return3m >= required_3m
                )
                else "CONDITIONS_NOT_MET"
            )

            rows.append({
                "run_id": self.run_id,
                "asset_id": asset,
                "current_action": current_action,
                "upgrade_action": upgrade_action,
                "upgrade_score_required": (
                    upgrade_score
                ),
                "upgrade_confidence_required": (
                    upgrade_confidence
                ),
                "upgrade_30d_return_required": (
                    required_30
                ),
                "upgrade_3m_return_required": (
                    required_3m
                ),
                "upgrade_condition": condition,
                "downgrade_action": (
                    downgrade_action
                ),
                "downgrade_score_threshold": (
                    downgrade_score
                ),
                "downgrade_30d_return_threshold": (
                    downgrade_return
                ),
                "downgrade_condition": (
                    downgrade_condition
                ),
                "current_distance_to_upgrade": (
                    distance
                ),
                "trigger_status": trigger_status,
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def thesis(self, current, projections):
        rows = []
        for _, row in current.iterrows():
            asset = row["asset_id"]
            score = safe_float(
                row["investment_score"]
            )
            action = str(
                row["best_action"]
            )
            price = safe_float(
                row["current_price"]
            )
            bear30 = self.projection_value(
                projections,
                asset,
                "30D",
                "bear_price",
            )
            median30 = self.projection_value(
                projections,
                asset,
                "30D",
            )
            bull3m = self.projection_value(
                projections,
                asset,
                "M03",
                "bull_price",
            )
            bear_return = (
                (bear30 / price - 1) * 100
                if price
                else 0.0
            )
            median_return = (
                (median30 / price - 1) * 100
                if price
                else 0.0
            )

            summary = (
                f"{asset.title()} is ranked "
                f"{self.conviction_tier(score)} "
                f"with action {action}."
            )
            support = (
                str(row["primary_reason"])
                + f" Bull 3M price scenario "
                f"{bull3m:,.2f}."
            )
            invalidation = (
                f"Invalidate the current thesis if "
                f"the score falls below "
                f"{self.cfg['downgrade_score']:.0f}, "
                f"the 30D median return weakens "
                f"below "
                f"{self.cfg['downgrade_30d_return']:.1f}%, "
                "or Module 42 changes the action "
                "to REDUCE/AVOID."
            )
            downside = (
                f"30D bear case implies "
                f"{bear_return:.1f}% versus current; "
                f"30D median implies "
                f"{median_return:.1f}%."
            )
            priority = (
                "HIGH"
                if action in {
                    "STRONG_BUY",
                    "BUY",
                    "SCALE_IN",
                    "REDUCE",
                }
                else "MEDIUM"
                if score >= 40
                else "LOW"
            )
            status = (
                "ACTIVE"
                if action in {
                    "STRONG_BUY",
                    "BUY",
                    "SCALE_IN",
                }
                else "WATCH"
                if action in {"HOLD", "WAIT"}
                else "DEFENSIVE"
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": asset,
                "thesis_summary": summary,
                "supporting_evidence": support,
                "invalidation_condition": (
                    invalidation
                ),
                "downside_risk": downside,
                "monitoring_priority": priority,
                "thesis_status": status,
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def timing(self, current, projections):
        rows = []
        for _, row in current.iterrows():
            asset = row["asset_id"]
            current_price = safe_float(
                row["current_price"]
            )
            price7 = self.projection_value(
                projections,
                asset,
                "7D",
            )
            price30 = self.projection_value(
                projections,
                asset,
                "30D",
            )
            price3m = self.projection_value(
                projections,
                asset,
                "M03",
            )
            buy_now_30 = (
                (price30 / current_price - 1)
                * 100
                if current_price
                else 0.0
            )
            wait7_then30 = (
                (price30 / price7 - 1) * 100
                if price7
                else 0.0
            )
            wait30_then3m = (
                (price3m / price30 - 1) * 100
                if price30
                else 0.0
            )
            wait_advantage = (
                (
                    current_price / price7 - 1
                )
                * 100
                if price7
                else 0.0
            )
            action = str(row["best_action"])
            if action in {
                "STRONG_BUY",
                "BUY",
            } and buy_now_30 > 0:
                preference = "BUY_NOW"
            elif action == "SCALE_IN":
                preference = "SCALE_IN"
            elif price7 < current_price:
                preference = "WAIT_FOR_7D_ENTRY"
            elif price30 < current_price:
                preference = "WAIT_FOR_30D_ENTRY"
            else:
                preference = "NO_CLEAR_TIMING_EDGE"

            confidence = clip(
                safe_float(
                    row["forecast_confidence"]
                )
                * (
                    1
                    if row["evidence_status"]
                    == "LIVE_VALIDATED"
                    else 0.65
                ),
                0.05,
                0.95,
            )
            reason = (
                f"Current {current_price:,.2f}; "
                f"7D median {price7:,.2f}; "
                f"30D median {price30:,.2f}; "
                f"3M median {price3m:,.2f}."
            )
            rows.append({
                "run_id": self.run_id,
                "asset_id": asset,
                "current_action": action,
                "current_price": current_price,
                "median_7d_price": price7,
                "median_30d_price": price30,
                "median_3m_price": price3m,
                "buy_now_30d_return_pct": (
                    buy_now_30
                ),
                "wait_7d_then_30d_return_pct": (
                    wait7_then30
                ),
                "wait_30d_then_3m_return_pct": (
                    wait30_then3m
                ),
                "estimated_wait_advantage_pct": (
                    wait_advantage
                ),
                "timing_preference": preference,
                "timing_confidence": confidence,
                "timing_reason": reason,
                "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def committee(
        self,
        summary,
        ranking,
        changes,
        triggers,
    ):
        top = ranking.iloc[0]
        material = changes[
            changes["change_classification"]
            == "MATERIAL_CHANGE"
        ]
        key_change = (
            material.iloc[0]["change_summary"]
            if not material.empty
            else changes.iloc[0]["change_summary"]
        )
        ready = triggers[
            triggers["trigger_status"]
            == "UPGRADE_READY"
        ]
        conditions_to_deploy = (
            "; ".join(
                ready["upgrade_condition"].head(
                    3
                ).tolist()
            )
            if not ready.empty
            else (
                "No asset currently meets the full "
                "upgrade criteria. Reassess when "
                "scores, confidence, and 30D/3M "
                "returns satisfy the trigger table."
            )
        )
        target_crypto = (
            safe_float(
                summary["target_risk_weight"]
            )
            * 100
        )
        target_cash = (
            safe_float(
                summary["target_cash_weight"]
            )
            * 100
        )
        decision = str(
            summary["overall_action"]
        )
        capital_posture = (
            "DEFENSIVE"
            if decision == "REMAIN_DEFENSIVE"
            else "SELECTIVE"
            if decision
            == "SELECTIVE_ACCUMULATION"
            else "DEPLOYING"
        )
        rationale = (
            f"Maintain {target_cash:.2f}% cash "
            f"and {target_crypto:.2f}% crypto. "
            f"Top relative opportunity is "
            f"{top['asset_id']} at score "
            f"{top['investment_score']:.1f}, "
            f"action {top['best_action']}. "
            "No capital is deployed unless "
            "Module 42 and Module 43 triggers agree."
        )
        primary_risk = (
            "Forecast reliability remains limited "
            "while live outcomes accumulate; "
            "long-range values are scenarios."
        )
        conditions_to_reduce = (
            f"Reduce when an asset score falls "
            f"below "
            f"{self.cfg['downgrade_score']:.0f}, "
            f"30D median return falls below "
            f"{self.cfg['downgrade_30d_return']:.1f}%, "
            "or the action becomes REDUCE/AVOID."
        )
        return pd.DataFrame([{
            "run_id": self.run_id,
            "recommendation_date": summary[
                "recommendation_date"
            ],
            "committee_decision": decision,
            "capital_posture": capital_posture,
            "review_window": summary[
                "overall_timeline"
            ],
            "target_crypto_pct": target_crypto,
            "target_cash_pct": target_cash,
            "highest_ranked_asset": top[
                "asset_id"
            ],
            "highest_ranked_score": top[
                "investment_score"
            ],
            "key_change": key_change,
            "primary_risk": primary_risk,
            "decision_rationale": rationale,
            "conditions_to_deploy": (
                conditions_to_deploy
            ),
            "conditions_to_reduce": (
                conditions_to_reduce
            ),
            "evidence_status": summary[
                "evidence_status"
            ],
            "calculated_at_utc": utcnow(),
        }])

    def run(self):
        self.conn.execute(
            """
            INSERT INTO module43_runs(
                run_id,
                source_module42_run_id,
                prior_module42_run_id,
                started_at_utc,
                completed_at_utc,
                status,
                ranked_assets,
                change_rows,
                trigger_rows,
                thesis_rows,
                timing_rows,
                committee_rows,
                positive_actions,
                material_changes,
                evidence_status,
                committee_decision,
                recommendation,
                notes,
                platform_version
            )
            VALUES(
                ?,?,?,?,NULL,'RUNNING',
                0,0,0,0,0,0,0,0,
                NULL,NULL,NULL,NULL,'12.1.0'
            )
            """,
            [
                self.run_id,
                self.source42,
                self.prior42,
                self.started,
            ],
        )

        try:
            current = self.recommendations(
                self.source42
            )
            current_projection = self.projections(
                self.source42
            )
            summary = self.summary(
                self.source42
            )
            prior = (
                self.recommendations(
                    self.prior42
                )
                if self.prior42
                else pd.DataFrame()
            )
            prior_projection = (
                self.projections(
                    self.prior42
                )
                if self.prior42
                else pd.DataFrame()
            )

            ranking = self.ranking(current)
            changes = self.changes(
                current,
                current_projection,
                prior,
                prior_projection,
            )
            triggers = self.triggers(
                current,
                current_projection,
            )
            thesis = self.thesis(
                current,
                current_projection,
            )
            timing = self.timing(
                current,
                current_projection,
            )
            committee = self.committee(
                summary,
                ranking,
                changes,
                triggers,
            )

            for table, frame in [
                (
                    "m43_opportunity_ranking",
                    ranking,
                ),
                (
                    "m43_decision_changes",
                    changes,
                ),
                (
                    "m43_action_triggers",
                    triggers,
                ),
                (
                    "m43_thesis_monitor",
                    thesis,
                ),
                (
                    "m43_buy_wait_analysis",
                    timing,
                ),
                (
                    "m43_committee_brief",
                    committee,
                ),
            ]:
                self.upsert(table, frame)

            positive = int(
                current["best_action"].isin(
                    {
                        "STRONG_BUY",
                        "BUY",
                        "SCALE_IN",
                    }
                ).sum()
            )
            material = int(
                (
                    changes[
                        "change_classification"
                    ]
                    == "MATERIAL_CHANGE"
                ).sum()
            )
            evidence = str(
                summary["evidence_status"]
            )
            decision = str(
                committee.iloc[0][
                    "committee_decision"
                ]
            )
            recommendation = (
                "FOLLOW_COMMITTEE_BRIEF"
                if evidence == "LIVE_VALIDATED"
                else "USE_WITH_EVIDENCE_CAUTION"
            )
            notes = (
                "Ranked opportunities, prior-run changes, "
                "action upgrade/downgrade triggers, thesis "
                "invalidation rules, buy-versus-wait timing, "
                "and an investment-committee brief completed."
            )

            self.conn.execute(
                """
                UPDATE module43_runs
                SET completed_at_utc=?,
                    status='SUCCESS',
                    ranked_assets=?,
                    change_rows=?,
                    trigger_rows=?,
                    thesis_rows=?,
                    timing_rows=?,
                    committee_rows=?,
                    positive_actions=?,
                    material_changes=?,
                    evidence_status=?,
                    committee_decision=?,
                    recommendation=?,
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    len(ranking),
                    len(changes),
                    len(triggers),
                    len(thesis),
                    len(timing),
                    len(committee),
                    positive,
                    material,
                    evidence,
                    decision,
                    recommendation,
                    notes,
                    self.run_id,
                ],
            )
            self.conn.close()
            return committee.iloc[0].to_dict()

        except Exception as exc:
            self.conn.execute(
                """
                UPDATE module43_runs
                SET completed_at_utc=?,
                    status='FAILED',
                    notes=?
                WHERE run_id=?
                """,
                [
                    utcnow(),
                    str(exc)[:1000],
                    self.run_id,
                ],
            )
            self.conn.close()
            raise


def run_module43():
    return Module43Runner().run()
