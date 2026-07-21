from crypto_platform.module15 import run_module15

def main():
    print("Crypto Intelligence Platform — Module 15 v15.0")
    print("Research, strategy calibration, and walk-forward selection\n")
    result = run_module15()
    print("Module 15 summary")
    print("-----------------")
    print(f"Status:                    {result['status']}")
    print(f"Variants tested:           {result['variants_tested']}")
    print(f"Walk-forward folds:        {result['walk_forward_folds']}")
    print(f"Selected variant:          {result['selected_variant']}")
    print(f"Out-of-sample return:      {result['oos_return_pct']:.2f}%")
    print(f"Out-of-sample BTC return:  {result['oos_btc_return_pct']:.2f}%")
    print(f"Out-of-sample excess:      {result['oos_excess_pct']:.2f}%")
    print(
        "Information ratio:         "
        + (
            f"{result['information_ratio']:.3f}"
            if result["information_ratio"] is not None
            else "N/A"
        )
    )
    print(f"Maximum drawdown:          {result['maximum_drawdown_pct']:.2f}%")
    print(f"Promotion candidate:       {result['promoted']}")
    print(f"Run ID:                    {result['run_id']}")

if __name__ == "__main__":
    main()
