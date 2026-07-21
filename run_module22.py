from crypto_platform.module22 import run_module22

def main():
    print("Crypto Intelligence Platform — Module 22 v22.0")
    print("Intelligence expansion, model selection, ensemble regimes, and six-asset allocation\n")
    r = run_module22()
    print("Module 22 summary")
    print("-----------------")
    print(f"Status:                  {r['status']}")
    print(f"Expanded features:       {r['expanded_features']}")
    print(f"Model comparison rows:   {r['model_rows']}")
    print(f"Selected models:         {r['selected_models']}")
    print(f"Allocation rows:         {r['allocation_rows']}")
    print(f"Walk-forward folds:      {r['walk_forward_folds']}")
    print(f"Portfolio return:        {r['portfolio_return_pct']}")
    print(f"Bitcoin return:          {r['btc_return_pct']}")
    print(f"Excess return:           {r['excess_return_pct']}")
    print(f"Information ratio:       {r['information_ratio']}")
    print(f"Promotion status:        {r['promotion_status']}")
    print(f"Run ID:                  {r['run_id']}")

if __name__ == "__main__":
    main()
