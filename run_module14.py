from crypto_platform.module14 import run_module14

def main():
    print("Crypto Intelligence Platform — Module 14 v14.0")
    print("Historical scoring and portfolio methodology validation\n")
    result = run_module14()
    print("Module 14 summary")
    print("-----------------")
    print(f"Status:                  {result['status']}")
    print(f"Rebalance periods:       {result['rebalance_periods']}")
    print(f"Validation rows:         {result['validation_rows']}")
    print(f"Portfolio return:        {result['portfolio_return_pct']:.2f}%")
    print(f"Bitcoin benchmark:       {result['benchmark_return_pct']:.2f}%")
    print(f"Excess return:           {result['excess_return_pct']:.2f}%")
    print(f"Maximum drawdown:        {result['maximum_drawdown_pct']:.2f}%")
    print(
        "Information ratio:       "
        + (
            f"{result['information_ratio']:.3f}"
            if result["information_ratio"] is not None
            else "N/A"
        )
    )
    print(f"Methodology promoted:    {result['promoted']}")
    print(f"Run ID:                  {result['run_id']}")

if __name__ == "__main__":
    main()
