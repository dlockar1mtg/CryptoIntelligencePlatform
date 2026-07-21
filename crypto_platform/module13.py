from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import requests

from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA, clamp
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA
from crypto_platform.module12 import MODULE12_SCHEMA

MODULE13_SCHEMA = r"""
CREATE TABLE IF NOT EXISTS module13_runs(
    run_id VARCHAR PRIMARY KEY,
    started_at_utc TIMESTAMPTZ,
    completed_at_utc TIMESTAMPTZ,
    status VARCHAR,
    assets_analyzed INTEGER,
    core_assets_recommended INTEGER,
    derivatives_provider VARCHAR,
    notes VARCHAR,
    platform_version VARCHAR
);

CREATE TABLE IF NOT EXISTS market_structure_daily(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    price_usd DOUBLE,
    history_days INTEGER,
    return_7d_pct DOUBLE,
    return_30d_pct DOUBLE,
    return_90d_pct DOUBLE,
    return_180d_pct DOUBLE,
    volatility_30d_pct DOUBLE,
    volatility_90d_pct DOUBLE,
    atr_14_pct DOUBLE,
    max_drawdown_365d_pct DOUBLE,
    recovery_from_drawdown_pct DOUBLE,
    sma_50 DOUBLE,
    sma_200 DOUBLE,
    price_vs_sma50_pct DOUBLE,
    price_vs_sma200_pct DOUBLE,
    trend_strength DOUBLE,
    momentum_score DOUBLE,
    correlation_btc DOUBLE,
    correlation_eth DOUBLE,
    beta_btc DOUBLE,
    sharpe_180d DOUBLE,
    sortino_180d DOUBLE,
    calmar_180d DOUBLE,
    liquidity_score DOUBLE,
    structure_quality VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS derivatives_signal_current(
    run_id VARCHAR,
    asset_id VARCHAR,
    provider VARCHAR,
    provider_symbol VARCHAR,
    funding_rate DOUBLE,
    open_interest DOUBLE,
    derivatives_score DOUBLE,
    derivatives_signal VARCHAR,
    provider_status VARCHAR,
    collected_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS investment_recommendations(
    run_id VARCHAR,
    asset_id VARCHAR,
    observation_date DATE,
    is_core BOOLEAN,
    sector VARCHAR,
    trend_score DOUBLE,
    momentum_score DOUBLE,
    value_score DOUBLE,
    risk_adjusted_score DOUBLE,
    relative_strength_score DOUBLE,
    liquidity_score DOUBLE,
    derivatives_score DOUBLE,
    overall_score DOUBLE,
    rating VARCHAR,
    confidence DOUBLE,
    risk_level VARCHAR,
    target_weight DOUBLE,
    recommendation_reason VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE TABLE IF NOT EXISTS portfolio_recommendation(
    run_id VARCHAR,
    asset_id VARCHAR,
    target_weight DOUBLE,
    score DOUBLE,
    rating VARCHAR,
    confidence DOUBLE,
    rationale VARCHAR,
    calculated_at_utc TIMESTAMPTZ,
    PRIMARY KEY(run_id, asset_id)
);

CREATE OR REPLACE VIEW latest_market_structure AS
SELECT x.* FROM market_structure_daily x
JOIN (SELECT run_id FROM module13_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);

CREATE OR REPLACE VIEW latest_investment_recommendations AS
SELECT x.* FROM investment_recommendations x
JOIN (SELECT run_id FROM module13_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);

CREATE OR REPLACE VIEW latest_portfolio_recommendation AS
SELECT x.* FROM portfolio_recommendation x
JOIN (SELECT run_id FROM module13_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id)
ORDER BY target_weight DESC;

CREATE OR REPLACE VIEW latest_derivatives_signals AS
SELECT x.* FROM derivatives_signal_current x
JOIN (SELECT run_id FROM module13_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
"""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def pct_return(series: pd.Series, days: int) -> float | None:
    if len(series) <= days:
        return None
    prior = float(series.iloc[-days-1])
    current = float(series.iloc[-1])
    if prior <= 0:
        return None
    return (current / prior - 1) * 100

def score_linear(value: float | None, bad: float, good: float) -> float:
    if value is None or pd.isna(value):
        return 50.0
    if good == bad:
        return 50.0
    return float(clamp((float(value)-bad)/(good-bad)*100))

def score_inverse(value: float | None, good: float, bad: float) -> float:
    return score_linear(value, bad, good)

def rating(score: float) -> str:
    if score >= 82: return "STRONG_BUY"
    if score >= 68: return "BUY"
    if score >= 48: return "HOLD"
    if score >= 35: return "REDUCE"
    return "AVOID"

class Module13Runner:
    def __init__(self):
        self.settings, self.assets = load_all()
        self.conn = connect(self.settings)
        for schema in [
            MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA,
            MODULE7_SCHEMA,MODULE8_SCHEMA,MODULE9_SCHEMA,MODULE10_SCHEMA,
            MODULE11_SCHEMA,MODULE12_SCHEMA,MODULE13_SCHEMA,
        ]:
            self.conn.execute(schema)
        self.config = self.settings["module13"]
        self.run_id = str(uuid.uuid4())
        self.started = utcnow()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent":"CryptoIntelligencePlatform/4.0"})

    def upsert(self, table: str, frame: pd.DataFrame) -> None:
        if frame.empty: return
        self.conn.register("_m13_stage", frame)
        cols = ",".join(frame.columns)
        self.conn.execute(f"INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _m13_stage")
        self.conn.unregister("_m13_stage")

    def histories(self) -> pd.DataFrame:
        frame = self.conn.execute("""
            SELECT asset_id,observation_date,price_usd,volume_24h_usd,source
            FROM research_market_daily
            WHERE price_usd IS NOT NULL
              AND observation_date>='2013-01-01'
            QUALIFY ROW_NUMBER() OVER(
                PARTITION BY asset_id,observation_date
                ORDER BY CASE source
                    WHEN 'binance' THEN 1
                    WHEN 'coinbase' THEN 2
                    WHEN 'kraken' THEN 3
                    WHEN 'coingecko_history' THEN 4
                    ELSE 9 END
            )=1
            ORDER BY asset_id,observation_date
        """).fetchdf()
        if not frame.empty:
            frame["observation_date"] = pd.to_datetime(frame["observation_date"])
        return frame

    def build_structure(self) -> pd.DataFrame:
        history = self.histories()
        minimum = int(self.config["market_structure"]["minimum_history_days"])
        risk_free = float(self.config["market_structure"]["risk_free_rate_pct"])/100
        price_maps = {
            aid:g.sort_values("observation_date").set_index("observation_date")["price_usd"].astype(float)
            for aid,g in history.groupby("asset_id")
        }
        btc = price_maps.get("bitcoin")
        eth = price_maps.get("ethereum")
        rows=[]
        for aid, group in history.groupby("asset_id"):
            group=group.sort_values("observation_date").drop_duplicates("observation_date",keep="last")
            s=group.set_index("observation_date")["price_usd"].astype(float)
            if len(s)<minimum: continue
            r=s.pct_change().dropna()
            current=float(s.iloc[-1])
            sma50=float(s.tail(50).mean())
            sma200=float(s.tail(200).mean()) if len(s)>=200 else None
            vol30=float(r.tail(30).std(ddof=1)*math.sqrt(365)*100) if len(r)>=30 else None
            vol90=float(r.tail(90).std(ddof=1)*math.sqrt(365)*100) if len(r)>=90 else None
            rolling_high=s.cummax()
            drawdowns=s/rolling_high-1
            maxdd=float(drawdowns.tail(365).min()*100)
            recovery=float((current/float(s.tail(365).min())-1)*100) if float(s.tail(365).min())>0 else None
            true_range=s.pct_change().abs().tail(14)
            atr=float(true_range.mean()*100)
            trend=(
                score_linear((current/sma50-1)*100,-20,20)*0.4+
                score_linear((current/sma200-1)*100 if sma200 else None,-35,35)*0.6
            )
            momentum=(
                score_linear(pct_return(s,30),-30,40)*0.35+
                score_linear(pct_return(s,90),-45,80)*0.40+
                score_linear(pct_return(s,180),-60,150)*0.25
            )
            corr_btc=corr_eth=beta_btc=None
            if btc is not None:
                aligned=pd.concat([s.pct_change(),btc.pct_change()],axis=1,join="inner").dropna().tail(180)
                if len(aligned)>=60:
                    corr_btc=float(aligned.iloc[:,0].corr(aligned.iloc[:,1]))
                    variance=float(aligned.iloc[:,1].var())
                    beta_btc=float(aligned.cov().iloc[0,1]/variance) if variance>0 else None
            if eth is not None:
                aligned=pd.concat([s.pct_change(),eth.pct_change()],axis=1,join="inner").dropna().tail(180)
                if len(aligned)>=60:
                    corr_eth=float(aligned.iloc[:,0].corr(aligned.iloc[:,1]))
            rr=r.tail(180)
            annual_return=float(rr.mean()*365)
            annual_vol=float(rr.std(ddof=1)*math.sqrt(365))
            sharpe=(annual_return-risk_free)/annual_vol if annual_vol>0 else None
            downside=float(rr[rr<0].std(ddof=1)*math.sqrt(365))
            sortino=(annual_return-risk_free)/downside if downside and downside>0 else None
            calmar=annual_return/abs(maxdd/100) if maxdd<0 else None
            volume=pd.to_numeric(group["volume_24h_usd"],errors="coerce").tail(30)
            median_volume=float(volume.median()) if volume.notna().any() else None
            liquidity=score_linear(math.log10(max(median_volume or 1,1)),5,10)
            quality="HIGH" if len(s)>=730 else "MEDIUM" if len(s)>=365 else "LIMITED"
            rows.append({
                "run_id":self.run_id,"asset_id":aid,"observation_date":s.index[-1].date(),
                "price_usd":current,"history_days":len(s),
                "return_7d_pct":pct_return(s,7),"return_30d_pct":pct_return(s,30),
                "return_90d_pct":pct_return(s,90),"return_180d_pct":pct_return(s,180),
                "volatility_30d_pct":vol30,"volatility_90d_pct":vol90,
                "atr_14_pct":atr,"max_drawdown_365d_pct":maxdd,
                "recovery_from_drawdown_pct":recovery,"sma_50":sma50,"sma_200":sma200,
                "price_vs_sma50_pct":(current/sma50-1)*100,
                "price_vs_sma200_pct":(current/sma200-1)*100 if sma200 else None,
                "trend_strength":trend,"momentum_score":momentum,
                "correlation_btc":corr_btc,"correlation_eth":corr_eth,"beta_btc":beta_btc,
                "sharpe_180d":sharpe,"sortino_180d":sortino,"calmar_180d":calmar,
                "liquidity_score":liquidity,"structure_quality":quality,
                "calculated_at_utc":utcnow(),
            })
        frame=pd.DataFrame(rows)
        self.upsert("market_structure_daily",frame)
        return frame

    def collect_derivatives(self, universe: pd.DataFrame) -> tuple[pd.DataFrame,str]:
        rows=[]; provider_used="UNAVAILABLE"; now=utcnow()
        # First use already-collected Binance data if available.
        existing=self.conn.execute("""
            SELECT f.asset_id,f.symbol,f.average_funding_rate,
                   o.open_interest_contracts
            FROM latest_derivatives_funding f
            LEFT JOIN (
                SELECT * EXCLUDE(rn) FROM (
                    SELECT *,ROW_NUMBER() OVER(
                        PARTITION BY asset_id ORDER BY observation_time_utc DESC
                    ) rn FROM derivatives_open_interest
                ) x WHERE rn=1
            ) o USING(asset_id)
        """).fetchdf()
        if not existing.empty:
            provider_used="binance"
            for _,r in existing.iterrows():
                funding=float(r["average_funding_rate"]) if pd.notna(r["average_funding_rate"]) else 0
                score=clamp(50-funding*100000)
                rows.append({
                    "run_id":self.run_id,"asset_id":r["asset_id"],"provider":"binance",
                    "provider_symbol":r["symbol"],"funding_rate":funding,
                    "open_interest":r["open_interest_contracts"],
                    "derivatives_score":score,
                    "derivatives_signal":"CROWDED_LONG" if score<35 else "CROWDED_SHORT" if score>65 else "NEUTRAL",
                    "provider_status":"ONLINE","collected_at_utc":now,
                })
        # Bybit public fallback for assets without Binance derivatives.
        covered={r["asset_id"] for r in rows}
        try:
            tickers=self.session.get(
                "https://api.bybit.com/v5/market/tickers",
                params={"category":"linear"},timeout=30
            )
            tickers.raise_for_status()
            items=tickers.json().get("result",{}).get("list",[])
            by_symbol={str(x.get("symbol","")).upper():x for x in items}
            for _,asset in universe.iterrows():
                if asset["asset_id"] in covered: continue
                symbol=f"{str(asset['symbol']).upper()}USDT"
                item=by_symbol.get(symbol)
                if not item: continue
                funding=float(item.get("fundingRate") or 0)
                oi=float(item.get("openInterest") or 0)
                score=clamp(50-funding*100000)
                rows.append({
                    "run_id":self.run_id,"asset_id":asset["asset_id"],"provider":"bybit",
                    "provider_symbol":symbol,"funding_rate":funding,"open_interest":oi,
                    "derivatives_score":score,
                    "derivatives_signal":"CROWDED_LONG" if score<35 else "CROWDED_SHORT" if score>65 else "NEUTRAL",
                    "provider_status":"ONLINE","collected_at_utc":now,
                })
            if rows and provider_used=="UNAVAILABLE": provider_used="bybit"
            elif rows and provider_used=="binance": provider_used="binance+bybit"
        except Exception:
            pass
        frame=pd.DataFrame(rows)
        self.upsert("derivatives_signal_current",frame)
        return frame,provider_used

    def recommendations(self, structure: pd.DataFrame, derivatives: pd.DataFrame) -> pd.DataFrame:
        if structure.empty: return pd.DataFrame()
        universe=self.conn.execute("""
            SELECT u.asset_id,u.symbol,u.market_cap_usd,u.volume_24h_usd,
                   u.ath_change_pct,COALESCE(t.sector,'OTHER') sector
            FROM latest_research_universe u
            LEFT JOIN research_asset_taxonomy t USING(asset_id)
        """).fetchdf()
        frame=structure.merge(universe,on="asset_id",how="left")
        if not derivatives.empty:
            frame=frame.merge(derivatives[["asset_id","derivatives_score"]],on="asset_id",how="left")
        else:
            frame["derivatives_score"]=50.0
        frame["derivatives_score"]=frame["derivatives_score"].fillna(50)
        core=set(self.config["recommendations"]["core_asset_ids"])
        w=self.config["recommendations"]["score_weights"]
        rows=[]
        for _,r in frame.iterrows():
            trend=float(r["trend_strength"])
            momentum=float(r["momentum_score"])
            value=score_inverse(abs(float(r["ath_change_pct"] or -30)),15,85)
            risk_adj=np.mean([
                score_linear(r["sharpe_180d"],-1,2),
                score_linear(r["sortino_180d"],-1,3),
                score_linear(r["calmar_180d"],-0.5,3),
                score_inverse(r["volatility_90d_pct"],35,180),
            ])
            rel=np.mean([
                score_inverse(abs((r["beta_btc"] if pd.notna(r["beta_btc"]) else 1)-1),0,2),
                score_linear(r["return_90d_pct"],-50,100),
            ])
            overall=(
                trend*float(w["trend"])+momentum*float(w["momentum"])+
                value*float(w["value"])+risk_adj*float(w["risk_adjusted"])+
                rel*float(w["relative_strength"])+float(r["liquidity_score"])*float(w["liquidity"])+
                float(r["derivatives_score"])*float(w["derivatives"])
            )
            confidence=clamp(
                45+
                min(25,float(r["history_days"])/1095*25)+
                (10 if r["structure_quality"]=="HIGH" else 5 if r["structure_quality"]=="MEDIUM" else 0)
            )
            risk="LOW" if (r["volatility_90d_pct"] or 999)<55 else "MEDIUM" if (r["volatility_90d_pct"] or 999)<100 else "HIGH"
            reasons=[
                f"trend {trend:.0f}",
                f"momentum {momentum:.0f}",
                f"risk-adjusted {risk_adj:.0f}",
                f"90d return {float(r['return_90d_pct'] or 0):.1f}%",
            ]
            rows.append({
                "run_id":self.run_id,"asset_id":r["asset_id"],
                "observation_date":r["observation_date"],"is_core":r["asset_id"] in core,
                "sector":r["sector"],"trend_score":trend,"momentum_score":momentum,
                "value_score":value,"risk_adjusted_score":risk_adj,
                "relative_strength_score":rel,"liquidity_score":r["liquidity_score"],
                "derivatives_score":r["derivatives_score"],"overall_score":overall,
                "rating":rating(overall),"confidence":confidence,"risk_level":risk,
                "target_weight":0.0,"recommendation_reason":"; ".join(reasons),
                "calculated_at_utc":utcnow(),
            })
        result=pd.DataFrame(rows)
        self.upsert("investment_recommendations",result)
        return result

    def portfolio(self, recommendations: pd.DataFrame) -> pd.DataFrame:
        if recommendations.empty:return pd.DataFrame()
        core=recommendations[recommendations["is_core"]].copy()
        floor=float(self.config["recommendations"]["minimum_cash_weight"])
        ceiling=float(self.config["recommendations"]["maximum_cash_weight"])
        average_score=float(core["overall_score"].mean())
        cash=clamp((60-average_score)/60*100,floor*100,ceiling*100)/100
        investable=1-cash
        raw=np.maximum(core["overall_score"].to_numpy()-30,1)
        risk_penalty=core["risk_level"].map({"LOW":1.0,"MEDIUM":0.8,"HIGH":0.55}).to_numpy()
        raw=raw*risk_penalty
        weights=raw/raw.sum()*investable
        max_weight=float(self.config["recommendations"]["maximum_single_asset_weight"])
        # Iterative cap and redistribute.
        for _ in range(10):
            excess=np.maximum(weights-max_weight,0).sum()
            weights=np.minimum(weights,max_weight)
            uncapped=weights<max_weight-1e-9
            if excess<=1e-9 or not uncapped.any():break
            weights[uncapped]+=excess*weights[uncapped]/weights[uncapped].sum()
        rows=[]
        for (_,r),weight in zip(core.iterrows(),weights):
            rows.append({
                "run_id":self.run_id,"asset_id":r["asset_id"],
                "target_weight":float(weight),"score":r["overall_score"],
                "rating":r["rating"],"confidence":r["confidence"],
                "rationale":r["recommendation_reason"],
                "calculated_at_utc":utcnow(),
            })
        rows.append({
            "run_id":self.run_id,"asset_id":"CASH","target_weight":float(cash),
            "score":100-cash*100,"rating":"RESERVE","confidence":80.0,
            "rationale":"Dynamic reserve based on average core-asset opportunity score.",
            "calculated_at_utc":utcnow(),
        })
        frame=pd.DataFrame(rows)
        self.upsert("portfolio_recommendation",frame)
        return frame

    def run(self) -> dict[str,Any]:
        self.conn.execute("""
            INSERT INTO module13_runs(
                run_id,started_at_utc,status,assets_analyzed,
                core_assets_recommended,derivatives_provider,notes,platform_version
            ) VALUES (?,?,'RUNNING',0,0,NULL,NULL,'4.0.0')
        """,[self.run_id,self.started])
        # Apply the exclusions that v3.2 did not persist reliably.
        exclusions=self.config["exclusions"]["asset_ids"]
        if exclusions:
            marks=",".join(["?"]*len(exclusions))
            self.conn.execute(
                f"UPDATE research_universe SET inclusion_status='EXCLUDED', "
                f"inclusion_reason='Excluded by v3.3 optimization.' "
                f"WHERE asset_id IN ({marks})",exclusions
            )
        structure=self.build_structure()
        universe=self.conn.execute("SELECT * FROM latest_research_universe").fetchdf()
        derivatives,provider=self.collect_derivatives(universe)
        recs=self.recommendations(structure,derivatives)
        portfolio=self.portfolio(recs)
        notes=f"structure={len(structure)}; derivatives={len(derivatives)}; recommendations={len(recs)}; portfolio={len(portfolio)}."
        self.conn.execute("""
            UPDATE module13_runs SET completed_at_utc=?,status='SUCCESS',
            assets_analyzed=?,core_assets_recommended=?,derivatives_provider=?,notes=?
            WHERE run_id=?
        """,[utcnow(),len(structure),int(recs["is_core"].sum()) if not recs.empty else 0,provider,notes,self.run_id])
        self.conn.close()
        return {
            "run_id":self.run_id,"status":"SUCCESS","assets_analyzed":len(structure),
            "recommendations":len(recs),"portfolio_rows":len(portfolio),
            "derivatives_rows":len(derivatives),"derivatives_provider":provider,
        }

def run_module13() -> dict[str,Any]:
    return Module13Runner().run()
