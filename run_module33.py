from crypto_platform.module33 import run_module33


def main():
    print("Crypto Intelligence Platform — Module 33 v33.0")
    print("Portfolio Decision Optimization & Drift Repair\n")
    result = run_module33()

    print("Module 33 summary")
    print("-----------------")
    print(
        f"Selected candidate:          "
        f"{result['selected_candidate_id']}"
    )
    print(
        f"Temperature:                 "
        f"{result['temperature']:.2f}"
    )
    print(
        f"Switch margin:               "
        f"{result['switch_margin']:.2f}"
    )
    print(
        f"Minimum hold days:           "
        f"{int(result['minimum_hold_days'])}"
    )
    print(
        f"Confidence floor:            "
        f"{result['confidence_floor']:.2f}"
    )
    print(
        f"Maximum risk exposure:       "
        f"{result['maximum_risk_exposure']:.2f}"
    )
    print(
        f"Adjusted drift:              "
        f"{result['adjusted_drift_status']}"
    )
    print(
        f"Optimized Sharpe:            "
        f"{result['optimized_sharpe']:.4f}"
    )
    print(
        f"BTC Sharpe:                  "
        f"{result['btc_sharpe']:.4f}"
    )
    print(
        f"Optimized max drawdown:      "
        f"{result['optimized_max_drawdown_pct']:.2f}%"
    )
    print(
        f"BTC max drawdown:            "
        f"{result['btc_max_drawdown_pct']:.2f}%"
    )
    print(
        f"Optimized turnover:          "
        f"{result['optimized_turnover_pct']:.2f}%"
    )
    print(
        f"Cost sensitivity pass rate:  "
        f"{result['cost_sensitivity_pass_rate_pct']:.2f}%"
    )
    print(
        f"Validation status:           "
        f"{result['validation_status']}"
    )
    print(
        f"Recommendation:              "
        f"{result['advancement_recommendation']}"
    )


if __name__ == "__main__":
    main()
