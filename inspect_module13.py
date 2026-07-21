from crypto_platform.platform import load_all,connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA
from crypto_platform.module12 import MODULE12_SCHEMA
from crypto_platform.module13 import MODULE13_SCHEMA

def show(c,title,sql):
    print(f"\n{title}\n"+("-"*len(title)))
    f=c.execute(sql).fetchdf()
    print(f.to_string(index=False) if not f.empty else "No data.")

def main():
    s,_=load_all(); c=connect(s)
    for schema in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA,MODULE7_SCHEMA,MODULE8_SCHEMA,MODULE9_SCHEMA,MODULE10_SCHEMA,MODULE11_SCHEMA,MODULE12_SCHEMA,MODULE13_SCHEMA]:
        c.execute(schema)
    show(c,"CORE PORTFOLIO RECOMMENDATION","SELECT asset_id,target_weight,score,rating,confidence,rationale FROM latest_portfolio_recommendation")
    show(c,"TOP INVESTMENT RECOMMENDATIONS","SELECT asset_id,sector,overall_score,rating,confidence,risk_level,trend_score,momentum_score,risk_adjusted_score,relative_strength_score,derivatives_score FROM latest_investment_recommendations ORDER BY overall_score DESC LIMIT 25")
    show(c,"CORE MARKET STRUCTURE","SELECT m.asset_id,m.price_usd,m.return_30d_pct,m.return_90d_pct,m.volatility_90d_pct,m.max_drawdown_365d_pct,m.correlation_btc,m.beta_btc,m.sharpe_180d,m.sortino_180d,m.calmar_180d,m.structure_quality FROM latest_market_structure m WHERE m.asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche') ORDER BY m.asset_id")
    show(c,"DERIVATIVES SIGNALS","SELECT * FROM latest_derivatives_signals ORDER BY derivatives_score DESC")
    show(c,"LATEST MODULE 13 RUNS","SELECT started_at_utc,completed_at_utc,status,assets_analyzed,core_assets_recommended,derivatives_provider,notes FROM module13_runs ORDER BY started_at_utc DESC LIMIT 10")
    c.close()
if __name__=="__main__": main()
