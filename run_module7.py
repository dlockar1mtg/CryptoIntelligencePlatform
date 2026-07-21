from crypto_platform.module7 import run_module7

def main():
    print("Crypto Intelligence Platform — Module 7 v7.0")
    print("Model calibration, feature importance, and walk-forward validation\n")
    result = run_module7()
    print("Module 7 summary")
    print("----------------")
    print(f"Status:                  {result['status']}")
    print(f"Primary horizon:         {result['primary_horizon_days']} days")
    print(f"Calibration samples:     {result['calibration_samples']}")
    print(f"Walk-forward folds:      {result['walk_forward_folds']}")
    print(f"Learned thresholds:      {result['learned_thresholds']}")
    print(f"Recommended thresholds:  {result['thresholds_recommended']}")
    print(f"Run ID:                  {result['run_id']}")

if __name__ == "__main__":
    main()
