from crypto_platform.module9 import run_module9

def main():
    print("Crypto Intelligence Platform — Module 9 v9.0")
    print("Calibrated regression, classification, and regime-aware prediction\n")
    result = run_module9()
    print("Module 9 summary")
    print("----------------")
    print(f"Status:                 {result['status']}")
    print(f"Training rows:          {result['training_rows']}")
    print(f"Walk-forward folds:     {result['validation_folds']}")
    print(f"Predictive weight:      {result['predictive_weight']:.1%}")
    print(f"Promoted:               {result['promoted']}")
    print(f"Current predictions:    {result['prediction_count']}")
    print(f"Run ID:                 {result['run_id']}")

if __name__ == "__main__":
    main()
