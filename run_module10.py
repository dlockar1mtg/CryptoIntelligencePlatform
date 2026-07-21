from crypto_platform.module10 import run_module10

def main():
    print("Crypto Intelligence Platform — Module 10 v10.0")
    print("Research-universe expansion, derivatives, sentiment, DeFi, and calibration\n")
    result = run_module10()
    print("Module 10 summary")
    print("-----------------")
    print(f"Status:                    {result['status']}")
    print(f"Assets discovered:         {result['discovered_assets']}")
    print(f"Assets selected:           {result['selected_assets']}")
    print(f"Historical rows processed: {result['history_rows']}")
    print(f"Derivative rows:           {result['derivative_rows']}")
    print(f"Sentiment rows:            {result['sentiment_rows']}")
    print(f"Calibrated predictions:    {result['calibrated_predictions']}")
    print(f"Run ID:                    {result['run_id']}")

if __name__ == "__main__":
    main()
