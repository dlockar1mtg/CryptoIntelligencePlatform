from crypto_platform.module25_validation import run_module25_validation

def main():
    print("Crypto Intelligence Platform — Module 25V")
    print("Regime Validation & Robustness\n")
    r = run_module25_validation()
    print("Module 25V summary")
    print("------------------")
    print(f"Walk-forward days:              {int(r['walk_forward_days'])}")
    print(f"Walk-forward agreement:         {r['walk_forward_agreement_pct']:.2f}%")
    print(f"Event windows covered:          {int(r['event_windows_covered'])}/{int(r['event_windows_total'])}")
    print(f"Probability calibration MAE:    {r['probability_calibration_mae']:.4f}")
    print(f"Sensitivity scenarios:          {int(r['sensitivity_scenarios'])}")
    print(f"Sensitivity stability:          {r['sensitivity_stability_pct']:.2f}%")
    print(f"Regime/asset rows:              {int(r['regime_asset_rows'])}")
    print(f"Module 13 history status:       {r['module13_history_status']}")
    print(f"Validation status:              {r['validation_status']}")
    print(f"Recommendation:                 {r['promotion_recommendation']}")

if __name__ == "__main__":
    main()
