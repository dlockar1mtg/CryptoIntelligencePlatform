from crypto_platform.module34 import run_module34

def main():
    print("Crypto Intelligence Platform — Module 34 v34.0")
    print("Institutional Portfolio Execution Engine\n")
    r=run_module34()
    print("Module 34 summary")
    print("-----------------")
    print(f"Selected candidate:          {r['selected_candidate_id']}")
    print(f"Rebalance frequency:         {int(r['rebalance_frequency_days'])} days")
    print(f"Rebalance band:              {r['rebalance_band_pct']:.2f}%")
    print(f"Minimum trade:               {r['minimum_trade_pct']:.2f}%")
    print(f"Exposure smoothing alpha:    {r['exposure_smoothing_alpha']:.2f}")
    print(f"Annual turnover budget:      {r['annual_turnover_budget_pct']:.2f}%")
    print(f"Execution drift:             {r['execution_drift_status']}")
    print(f"Optimized Sharpe:            {r['optimized_sharpe']:.4f}")
    print(f"BTC Sharpe:                  {r['btc_sharpe']:.4f}")
    print(f"Optimized max drawdown:      {r['optimized_max_drawdown_pct']:.2f}%")
    print(f"BTC max drawdown:            {r['btc_max_drawdown_pct']:.2f}%")
    print(f"Optimized turnover:          {r['optimized_turnover_pct']:.2f}%")
    print(f"Trade days:                  {int(r['trade_days'])}")
    print(f"Total asset trades:          {int(r['total_trades'])}")
    print(f"Cost sensitivity pass rate:  {r['cost_sensitivity_pass_rate_pct']:.2f}%")
    print(f"Validation status:           {r['validation_status']}")
    print(f"Recommendation:              {r['advancement_recommendation']}")

if __name__=="__main__":
    main()
