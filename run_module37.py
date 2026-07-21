from crypto_platform.module37 import run_module37


def main():
    print("Crypto Intelligence Platform — Module 37 v37.0")
    print("Institutional Portfolio Optimizer\n")

    result = run_module37()

    print("Module 37 summary")
    print("-----------------")
    print(
        f"Selected method:             "
        f"{result['selected_method']}"
    )
    print(
        f"Expected return:             "
        f"{result['expected_return_pct']:.2f}%"
    )
    print(
        f"Expected volatility:         "
        f"{result['expected_volatility_pct']:.2f}%"
    )
    print(
        f"Expected Sharpe:             "
        f"{result['expected_sharpe']:.4f}"
    )
    print(
        f"Diversification ratio:       "
        f"{result['diversification_ratio']:.4f}"
    )
    print(
        f"Risky effective assets:      "
        f"{result['risky_sleeve_effective_assets']:.2f}"
    )
    print(
        f"Risky concentration:         "
        f"{result['risky_sleeve_concentration_pct']:.2f}%"
    )
    print(
        f"Cash weight:                 "
        f"{result['cash_weight']*100:.2f}%"
    )
    print(
        f"Estimated turnover:          "
        f"{result['turnover_pct']:.2f}%"
    )
    print(
        f"Active share:                "
        f"{result['active_share_pct']:.2f}%"
    )
    print(
        f"Information ratio:           "
        f"{result['information_ratio']:.4f}"
    )
    print(
        f"Recommendation:              "
        f"{result['recommendation']}"
    )
    print(
        f"Validation status:           "
        f"{result['validation_status']}"
    )


if __name__ == "__main__":
    main()
