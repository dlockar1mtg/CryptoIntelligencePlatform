from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA, REGIMES

MODULE25V_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module25v_runs(
    run_id VARCHAR PRIMARY KEY,
    source_module25_run_id VARCHAR,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    walk_forward_rows INTEGER,
    event_rows INTEGER,
    performance_rows INTEGER,
    calibration_rows INTEGER,
    sensitivity_rows INTEGER,
    walk_forward_agreement_pct DOUBLE,
    calibration_error DOUBLE,
    sensitivity_stability_pct DOUBLE,
    validation_status VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS m25v_walk_forward_regimes(
    run_id VARCHAR,
    observation_date DATE,
    training_start_date DATE,
    training_end_date DATE,
    test_window_number INTEGER,
    full_sample_regime VARCHAR,
    walk_forward_regime VARCHAR,
    walk_forward_confidence DOUBLE,
    label_match BOOLEAN,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, observation_date)
);

CREATE TABLE IF NOT EXISTS m25v_event_window_audit(
    run_id VARCHAR,
    event_key VARCHAR,
    event_name VARCHAR,
    event_date DATE,
    window_start_date DATE,
    window_end_date DATE,
    observations INTEGER,
    dominant_regime VARCHAR,
    dominant_share_pct DOUBLE,
    mean_macro_stress_pct DOUBLE,
    mean_volatility_shock_pct DOUBLE,
    mean_recovery_pct DOUBLE,
    regime_interpretation VARCHAR,
    coverage_status VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, event_key)
);

CREATE TABLE IF NOT EXISTS m25v_regime_asset_performance(
    run_id VARCHAR,
    regime VARCHAR,
    asset_id VARCHAR,
    observations INTEGER,
    mean_next_30d_return_pct DOUBLE,
    median_next_30d_return_pct DOUBLE,
    positive_next_30d_rate_pct DOUBLE,
    annualized_daily_volatility_pct DOUBLE,
    worst_next_30d_return_pct DOUBLE,
    best_next_30d_return_pct DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, regime, asset_id)
);

CREATE TABLE IF NOT EXISTS m25v_module13_regime_audit(
    run_id VARCHAR,
    audit_key VARCHAR,
    status VARCHAR,
    historical_snapshot_rows INTEGER,
    message VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, audit_key)
);

CREATE TABLE IF NOT EXISTS m25v_probability_calibration(
    run_id VARCHAR,
    confidence_bin VARCHAR,
    observations INTEGER,
    mean_predicted_persistence DOUBLE,
    observed_next_day_persistence DOUBLE,
    absolute_calibration_error DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, confidence_bin)
);

CREATE TABLE IF NOT EXISTS m25v_parameter_sensitivity(
    run_id VARCHAR,
    scenario_key VARCHAR,
    smoothing DOUBLE,
    rule_multiplier DOUBLE,
    risk_multiplier DOUBLE,
    recovery_multiplier DOUBLE,
    label_agreement_pct DOUBLE,
    mean_probability_shift DOUBLE,
    current_regime VARCHAR,
    current_confidence DOUBLE,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, scenario_key)
);

CREATE TABLE IF NOT EXISTS m25v_validation_summary(
    run_id VARCHAR PRIMARY KEY,
    walk_forward_days INTEGER,
    walk_forward_agreement_pct DOUBLE,
    event_windows_covered INTEGER,
    event_windows_total INTEGER,
    probability_calibration_mae DOUBLE,
    sensitivity_scenarios INTEGER,
    sensitivity_stability_pct DOUBLE,
    regime_asset_rows INTEGER,
    module13_history_status VARCHAR,
    validation_status VARCHAR,
    promotion_recommendation VARCHAR,
    calculated_at_utc TIMESTAMPTZ
);

CREATE OR REPLACE VIEW latest_m25v_walk_forward_regimes AS
SELECT * FROM m25v_walk_forward_regimes
WHERE run_id=(SELECT run_id FROM module25v_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY observation_date;

CREATE OR REPLACE VIEW latest_m25v_event_window_audit AS
SELECT * FROM m25v_event_window_audit
WHERE run_id=(SELECT run_id FROM module25v_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY event_date;

CREATE OR REPLACE VIEW latest_m25v_regime_asset_performance AS
SELECT * FROM m25v_regime_asset_performance
WHERE run_id=(SELECT run_id FROM module25v_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY regime, mean_next_30d_return_pct DESC;

CREATE OR REPLACE VIEW latest_m25v_module13_regime_audit AS
SELECT * FROM m25v_module13_regime_audit
WHERE run_id=(SELECT run_id FROM module25v_runs ORDER BY started_at_utc DESC LIMIT 1);

CREATE OR REPLACE VIEW latest_m25v_probability_calibration AS
SELECT * FROM m25v_probability_calibration
WHERE run_id=(SELECT run_id FROM module25v_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY confidence_bin;

CREATE OR REPLACE VIEW latest_m25v_parameter_sensitivity AS
SELECT * FROM m25v_parameter_sensitivity
WHERE run_id=(SELECT run_id FROM module25v_runs ORDER BY started_at_utc DESC LIMIT 1)
ORDER BY scenario_key;

CREATE OR REPLACE VIEW latest_m25v_validation_summary AS
SELECT * FROM m25v_validation_summary
WHERE run_id=(SELECT run_id FROM module25v_runs ORDER BY started_at_utc DESC LIMIT 1);
"""

EVENTS = [
    ("COVID_CRASH", "COVID-19 market crash", "2020-03-12"),
    ("TERRA_COLLAPSE", "Terra/Luna collapse", "2022-05-09"),
    ("FTX_BANKRUPTCY", "FTX bankruptcy", "2022-11-11"),
    ("SPOT_BTC_ETF", "U.S. spot Bitcoin ETF launch", "2024-01-11"),
    ("BTC_HALVING_2024", "2024 Bitcoin halving", "2024-04-20"),
]

def utcnow():
    return datetime.now(timezone.utc)

def safe(value: Any, default: float = 0.0):
    if value is None or pd.isna(value):
        return float(default)
    return float(value)

def softmax(values):
    values = np.asarray(values, dtype=float)
    values = values - np.max(values)
    exp = np.exp(np.clip(values, -50, 50))
    return exp / exp.sum()

class Module25ValidationRunner:
    def __init__(self):
        self.settings, _ = load_all()
        self.conn = connect(self.settings)
        self.conn.execute(MODULE25_SCHEMA)
        self.conn.execute(MODULE25V_SCHEMA)
        self.cfg = self.settings["module25_validation"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        row = self.conn.execute(
            "SELECT run_id FROM module25_runs WHERE status='SUCCESS' "
            "ORDER BY started_at_utc DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("No successful Module 25 run is available.")
        self.source_run_id = str(row[0])

    def upsert(self, table, frame):
        if frame.empty:
            return
        self.conn.register("_m25v_stage", frame)
        columns = ",".join(frame.columns)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table}({columns}) "
            f"SELECT {columns} FROM _m25v_stage"
        )
        self.conn.unregister("_m25v_stage")

    def features(self):
        frame = self.conn.execute(
            "SELECT * FROM m25_regime_features WHERE run_id=? "
            "ORDER BY observation_date",
            [self.source_run_id],
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.set_index("observation_date")

    def probabilities(self):
        frame = self.conn.execute(
            "SELECT * FROM m25_regime_probabilities WHERE run_id=? "
            "ORDER BY observation_date",
            [self.source_run_id],
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.set_index("observation_date")

    def prices(self):
        frame = self.conn.execute(
            "SELECT asset_id, observation_date, price_usd "
            "FROM canonical_market_daily "
            "WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') "
            "AND price_usd IS NOT NULL ORDER BY observation_date, asset_id"
        ).fetchdf()
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame.pivot(
            index="observation_date", columns="asset_id", values="price_usd"
        ).sort_index()

    @staticmethod
    def cluster_map(centers, scaler, columns):
        original = scaler.inverse_transform(centers)
        mapping = {}
        used = set()
        for idx, values in enumerate(original):
            row = pd.Series(values, index=columns)
            scores = np.array([
                1.4*safe(row.get("liquidity_score")) + .45*safe(row.get("trend_score")) - .3*safe(row.get("risk_score")),
                1.35*safe(row.get("trend_score")) + .25*safe(row.get("liquidity_score")) - .25*safe(row.get("risk_score")),
                1.35*safe(row.get("recovery_score")) + .35*safe(row.get("trend_score")),
                -.85*abs(safe(row.get("trend_score"))) - .55*abs(safe(row.get("liquidity_score"))),
                1.2*safe(row.get("risk_score")) - .8*safe(row.get("liquidity_score")) - .45*safe(row.get("trend_score")),
                1.35*safe(row.get("change_pressure")) + .8*safe(row.get("risk_score")),
            ])
            order = np.argsort(-scores)
            chosen = next((REGIMES[i] for i in order if REGIMES[i] not in used), REGIMES[order[0]])
            mapping[idx] = chosen
            used.add(chosen)
        return mapping

    def walk_forward(self, features, probabilities):
        columns = [
            "liquidity_score","trend_score","risk_score","recovery_score",
            "change_pressure","btc_return_90d","btc_distance_sma200",
            "btc_volatility_90d","btc_drawdown_180d","core_breadth",
            "stablecoin_growth_30d","high_yield_spread","dollar_index",
        ]
        matrix = features[columns].replace([np.inf,-np.inf], np.nan).dropna()
        train_days = int(self.cfg["walk_forward"]["minimum_training_days"])
        test_days = int(self.cfg["walk_forward"]["test_days"])
        rows = []
        window = 0
        start = train_days
        seed = int(self.cfg["walk_forward"]["random_state"])
        while start < len(matrix):
            end = min(start + test_days, len(matrix))
            train = matrix.iloc[:start]
            test = matrix.iloc[start:end]
            if len(test) == 0:
                break
            scaler = StandardScaler()
            x_train = scaler.fit_transform(train)
            x_test = scaler.transform(test)
            gmm = GaussianMixture(
                n_components=6, covariance_type="full", random_state=seed,
                reg_covar=1e-5, n_init=3
            ).fit(x_train)
            km = KMeans(n_clusters=6, random_state=seed, n_init=10).fit(x_train)
            gmap = self.cluster_map(gmm.means_, scaler, columns)
            kmap = self.cluster_map(km.cluster_centers_, scaler, columns)
            gp = gmm.predict_proba(x_test)
            kl = km.predict(x_test)
            window += 1
            for i, date in enumerate(test.index):
                gvote = np.zeros(6)
                for c in range(6):
                    gvote[REGIMES.index(gmap[c])] += gp[i,c]
                kvote = np.zeros(6)
                kvote[REGIMES.index(kmap[int(kl[i])])] = 1
                r = test.iloc[i]
                rule = softmax(np.array([
                    1.4*r["liquidity_score"]+.45*r["trend_score"]-.3*r["risk_score"],
                    1.35*r["trend_score"]+.25*r["liquidity_score"]-.25*r["risk_score"],
                    1.35*r["recovery_score"]+.35*r["trend_score"],
                    -.85*abs(r["trend_score"])-.55*abs(r["liquidity_score"]),
                    1.2*r["risk_score"]-.8*r["liquidity_score"]-.45*r["trend_score"],
                    1.35*r["change_pressure"]+.8*r["risk_score"],
                ]))
                combined = .40*gvote + .25*kvote + .35*rule
                combined = combined/combined.sum()
                regime = REGIMES[int(np.argmax(combined))]
                full = probabilities.loc[date, "dominant_regime"] if date in probabilities.index else None
                rows.append({
                    "run_id": self.run_id,
                    "observation_date": date.date(),
                    "training_start_date": train.index.min().date(),
                    "training_end_date": train.index.max().date(),
                    "test_window_number": window,
                    "full_sample_regime": full,
                    "walk_forward_regime": regime,
                    "walk_forward_confidence": float(combined.max()),
                    "label_match": bool(regime == full),
                    "calculated_at_utc": utcnow(),
                })
            start = end
        return pd.DataFrame(rows)

    def event_audit(self, probabilities):
        before = int(self.cfg["events"]["days_before"])
        after = int(self.cfg["events"]["days_after"])
        rows = []
        for key, name, date_text in EVENTS:
            event_date = pd.Timestamp(date_text)
            window = probabilities[
                (probabilities.index >= event_date-pd.Timedelta(days=before))
                & (probabilities.index <= event_date+pd.Timedelta(days=after))
            ]
            if window.empty:
                rows.append({
                    "run_id": self.run_id, "event_key": key, "event_name": name,
                    "event_date": event_date.date(),
                    "window_start_date": (event_date-pd.Timedelta(days=before)).date(),
                    "window_end_date": (event_date+pd.Timedelta(days=after)).date(),
                    "observations": 0, "dominant_regime": None,
                    "dominant_share_pct": None, "mean_macro_stress_pct": None,
                    "mean_volatility_shock_pct": None, "mean_recovery_pct": None,
                    "regime_interpretation": "No historical coverage in the current warehouse.",
                    "coverage_status": "NO_COVERAGE", "calculated_at_utc": utcnow(),
                })
                continue
            counts = window["dominant_regime"].value_counts()
            dominant = counts.index[0]
            share = counts.iloc[0]/len(window)*100
            rows.append({
                "run_id": self.run_id, "event_key": key, "event_name": name,
                "event_date": event_date.date(),
                "window_start_date": window.index.min().date(),
                "window_end_date": window.index.max().date(),
                "observations": len(window), "dominant_regime": dominant,
                "dominant_share_pct": float(share),
                "mean_macro_stress_pct": float(window["macro_stress_probability"].mean()*100),
                "mean_volatility_shock_pct": float(window["volatility_shock_probability"].mean()*100),
                "mean_recovery_pct": float(window["recovery_probability"].mean()*100),
                "regime_interpretation": (
                    f"{dominant} was the most frequent regime around the event "
                    f"({share:.1f}% of covered days)."
                ),
                "coverage_status": "COVERED", "calculated_at_utc": utcnow(),
            })
        return pd.DataFrame(rows)

    def regime_performance(self, probabilities, prices):
        regimes = probabilities["dominant_regime"].reindex(prices.index).ffill()
        rows = []
        for asset in prices.columns:
            future = prices[asset].shift(-30)/prices[asset]-1
            daily = prices[asset].pct_change(fill_method=None)
            sample = pd.DataFrame({"regime":regimes,"future":future,"daily":daily}).dropna()
            for regime, group in sample.groupby("regime"):
                rows.append({
                    "run_id": self.run_id, "regime": regime, "asset_id": asset,
                    "observations": len(group),
                    "mean_next_30d_return_pct": float(group["future"].mean()*100),
                    "median_next_30d_return_pct": float(group["future"].median()*100),
                    "positive_next_30d_rate_pct": float((group["future"]>0).mean()*100),
                    "annualized_daily_volatility_pct": float(group["daily"].std()*math.sqrt(365)*100),
                    "worst_next_30d_return_pct": float(group["future"].min()*100),
                    "best_next_30d_return_pct": float(group["future"].max()*100),
                    "calculated_at_utc": utcnow(),
                })
        return pd.DataFrame(rows)

    def module13_audit(self):
        tables = self.conn.execute(
            "SELECT lower(table_name) FROM information_schema.tables"
        ).fetchdf().iloc[:,0].tolist()
        candidates = [t for t in tables if "portfolio_recommendation" in t]
        historical_rows = 0
        status = "NOT_AVAILABLE"
        message = (
            "No reliable dated Module 13 allocation history was found. "
            "Regime-conditioned asset performance was calculated instead."
        )
        for table in candidates:
            cols = self.conn.execute(
                "SELECT lower(column_name) FROM information_schema.columns "
                "WHERE lower(table_name)=?",
                [table],
            ).fetchdf().iloc[:,0].tolist()
            if "run_id" in cols and "asset_id" in cols and "target_weight" in cols:
                historical_rows += int(self.conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0])
        if historical_rows > 20:
            status = "PARTIAL_HISTORY_FOUND"
            message = (
                f"Found {historical_rows} historical allocation rows, but dated "
                "regime-safe replay requires a dedicated recommendation timestamp audit."
            )
        return pd.DataFrame([{
            "run_id": self.run_id, "audit_key":"MODULE13_HISTORY",
            "status":status, "historical_snapshot_rows":historical_rows,
            "message":message, "calculated_at_utc":utcnow(),
        }])

    def calibration(self, probabilities):
        frame = probabilities.copy()
        frame["next_same"] = (
            frame["dominant_regime"].shift(-1) == frame["dominant_regime"]
        ).astype(float)
        frame = frame.iloc[:-1]
        bins = [0,.4,.5,.6,.7,.8,1.0001]
        labels = ["0-40%","40-50%","50-60%","60-70%","70-80%","80-100%"]
        frame["bin"] = pd.cut(frame["regime_confidence"], bins=bins, labels=labels, right=False)
        rows = []
        for label, group in frame.groupby("bin", observed=True):
            if group.empty:
                continue
            predicted = float(group["regime_confidence"].mean())
            observed = float(group["next_same"].mean())
            rows.append({
                "run_id":self.run_id, "confidence_bin":str(label),
                "observations":len(group),
                "mean_predicted_persistence":predicted,
                "observed_next_day_persistence":observed,
                "absolute_calibration_error":abs(predicted-observed),
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def sensitivity(self, features, probabilities):
        scenarios = [
            ("BASELINE", .75, 1.0, 1.0, 1.0),
            ("LOW_SMOOTHING", .60, 1.0, 1.0, 1.0),
            ("HIGH_SMOOTHING", .85, 1.0, 1.0, 1.0),
            ("RULE_PLUS_10", .75, 1.1, 1.0, 1.0),
            ("RISK_PLUS_10", .75, 1.0, 1.1, 1.0),
            ("RECOVERY_PLUS_10", .75, 1.0, 1.0, 1.1),
            ("RISK_MINUS_10", .75, 1.0, .9, 1.0),
            ("RECOVERY_MINUS_10", .75, 1.0, 1.0, .9),
        ]
        baseline_labels = probabilities["dominant_regime"]
        baseline_probs = probabilities[
            ["liquidity_expansion_probability","momentum_bull_probability",
             "recovery_probability","range_bound_probability",
             "macro_stress_probability","volatility_shock_probability"]
        ].to_numpy()
        rows = []
        index = probabilities.index
        for key, smoothing, rule_mult, risk_mult, recovery_mult in scenarios:
            generated = []
            previous = None
            for date in index:
                f = features.loc[date]
                scores = np.array([
                    1.4*safe(f["liquidity_score"])+.45*safe(f["trend_score"])-.3*safe(f["risk_score"])*risk_mult,
                    1.35*safe(f["trend_score"])+.25*safe(f["liquidity_score"])-.25*safe(f["risk_score"])*risk_mult,
                    (1.35*safe(f["recovery_score"])*recovery_mult+.35*safe(f["trend_score"])),
                    -.85*abs(safe(f["trend_score"]))-.55*abs(safe(f["liquidity_score"])),
                    1.2*safe(f["risk_score"])*risk_mult-.8*safe(f["liquidity_score"])-.45*safe(f["trend_score"]),
                    1.35*safe(f["change_pressure"])+.8*safe(f["risk_score"])*risk_mult,
                ])*rule_mult
                p = softmax(scores)
                if previous is not None:
                    p = previous*smoothing + p*(1-smoothing)
                    p = p/p.sum()
                generated.append(p)
                previous = p
            array = np.vstack(generated)
            labels = pd.Series([REGIMES[i] for i in np.argmax(array,axis=1)], index=index)
            agreement = float((labels==baseline_labels).mean()*100)
            shift = float(np.mean(np.abs(array-baseline_probs)))
            rows.append({
                "run_id":self.run_id,"scenario_key":key,"smoothing":smoothing,
                "rule_multiplier":rule_mult,"risk_multiplier":risk_mult,
                "recovery_multiplier":recovery_mult,
                "label_agreement_pct":agreement,"mean_probability_shift":shift,
                "current_regime":labels.iloc[-1],
                "current_confidence":float(array[-1].max()),
                "calculated_at_utc":utcnow(),
            })
        return pd.DataFrame(rows)

    def run(self):
        self.conn.execute(
            "INSERT INTO module25v_runs VALUES "
            "(?,?,?,NULL,'RUNNING',0,0,0,0,0,NULL,NULL,NULL,NULL,NULL,'7.0.3')",
            [self.run_id,self.source_run_id,self.started],
        )
        try:
            features = self.features()
            probabilities = self.probabilities()
            prices = self.prices()
            wf = self.walk_forward(features, probabilities)
            events = self.event_audit(probabilities)
            performance = self.regime_performance(probabilities, prices)
            module13 = self.module13_audit()
            calibration = self.calibration(probabilities)
            sensitivity = self.sensitivity(features, probabilities)

            for table, frame in [
                ("m25v_walk_forward_regimes",wf),
                ("m25v_event_window_audit",events),
                ("m25v_regime_asset_performance",performance),
                ("m25v_module13_regime_audit",module13),
                ("m25v_probability_calibration",calibration),
                ("m25v_parameter_sensitivity",sensitivity),
            ]:
                self.upsert(table, frame)

            wf_agreement = float(wf["label_match"].mean()*100) if not wf.empty else 0.0
            calibration_mae = float(calibration["absolute_calibration_error"].mean()) if not calibration.empty else 1.0
            sensitivity_stability = float(
                sensitivity.loc[sensitivity["scenario_key"]!="BASELINE","label_agreement_pct"].mean()
            ) if len(sensitivity)>1 else 0.0
            covered = int((events["coverage_status"]=="COVERED").sum())
            passed = (
                wf_agreement >= float(self.cfg["validation"]["minimum_walk_forward_agreement_pct"])
                and calibration_mae <= float(self.cfg["validation"]["maximum_calibration_mae"])
                and sensitivity_stability >= float(self.cfg["validation"]["minimum_sensitivity_stability_pct"])
            )
            status = "PASSED" if passed else "LIMITED"
            recommendation = (
                "REGIME_ENGINE_VALIDATED_FOR_SPECIALIST_RESEARCH"
                if passed else "RESEARCH_ONLY_PENDING_REFINEMENT"
            )
            summary = pd.DataFrame([{
                "run_id":self.run_id,"walk_forward_days":len(wf),
                "walk_forward_agreement_pct":wf_agreement,
                "event_windows_covered":covered,"event_windows_total":len(events),
                "probability_calibration_mae":calibration_mae,
                "sensitivity_scenarios":len(sensitivity),
                "sensitivity_stability_pct":sensitivity_stability,
                "regime_asset_rows":len(performance),
                "module13_history_status":module13.iloc[0]["status"],
                "validation_status":status,
                "promotion_recommendation":recommendation,
                "calculated_at_utc":utcnow(),
            }])
            self.upsert("m25v_validation_summary", summary)
            self.conn.execute(
                "UPDATE module25v_runs SET completed_at_utc=?,status='SUCCESS',"
                "walk_forward_rows=?,event_rows=?,performance_rows=?,calibration_rows=?,"
                "sensitivity_rows=?,walk_forward_agreement_pct=?,calibration_error=?,"
                "sensitivity_stability_pct=?,validation_status=?,notes=? WHERE run_id=?",
                [utcnow(),len(wf),len(events),len(performance),len(calibration),len(sensitivity),
                 wf_agreement,calibration_mae,sensitivity_stability,status,
                 "Module 25 validation is research-only and does not alter Modules 13 or 25.",
                 self.run_id],
            )
            self.conn.close()
            return summary.iloc[0].to_dict()
        except Exception as exc:
            self.conn.execute(
                "UPDATE module25v_runs SET completed_at_utc=?,status='FAILED',notes=? WHERE run_id=?",
                [utcnow(),str(exc)[:1000],self.run_id],
            )
            self.conn.close()
            raise

def run_module25_validation():
    return Module25ValidationRunner().run()
