from crypto_platform.module38 import run_module38


def main():
    print("Crypto Intelligence Platform — Module 38 v38.0")
    print("Predictive Intelligence Engine\n")

    result = run_module38()

    print("Module 38 summary")
    print("-----------------")
    print(
        f"Forecast rows:              "
        f"{int(result['forecast_rows'])}"
    )
    print(
        f"Portfolio horizon:          "
        f"{int(result['horizon_days'])} days"
    )
    print(
        f"Expected portfolio return:  "
        f"{result['expected_portfolio_return_pct']:.2f}%"
    )
    print(
        f"Lower forecast bound:       "
        f"{result['lower_portfolio_return_pct']:.2f}%"
    )
    print(
        f"Upper forecast bound:       "
        f"{result['upper_portfolio_return_pct']:.2f}%"
    )
    print(
        f"Probability positive:       "
        f"{result['probability_positive']*100:.2f}%"
    )
    print(
        f"Forecast confidence:        "
        f"{result['forecast_confidence']*100:.2f}%"
    )
    print(
        f"Predictive regime:          "
        f"{result['dominant_predictive_regime']}"
    )
    print(
        f"Regime confidence:          "
        f"{result['predictive_regime_confidence']*100:.2f}%"
    )
    print(
        f"Forecast risk status:       "
        f"{result['forecast_risk_status']}"
    )
    print(
        f"Recommendation:             "
        f"{result['recommendation']}"
    )
    print(
        f"Mean validation MAE:        "
        f"{result['mean_validation_mae_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()
