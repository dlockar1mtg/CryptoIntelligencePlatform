from crypto_platform.module27 import run_module27

def main():
    print("Crypto Intelligence Platform — Module 27 v27.0")
    print("Regime Representation & Optimization\n")
    r = run_module27()
    print("Module 27 summary")
    print("-----------------")
    print(f"Representation features:       {int(r['representation_features'])}")
    print(f"Random candidates per fold:    {int(r['random_candidates'])}")
    print(f"Outer folds:                   {int(r['outer_folds'])}")
    print(f"Nested test rows:              {int(r['nested_rows'])}")
    print(f"Nested agreement:              {r['nested_agreement_pct']:.2f}%")
    print(f"Raw calibration MAE:           {r['raw_calibration_mae']:.4f}")
    print(f"Calibrated MAE:                {r['calibrated_mae']:.4f}")
    print(f"Empirical stability:           {r['empirical_stability_pct']:.2f}%")
    print(f"Current research regime:       {r['current_regime']}")
    print(f"Current calibrated confidence: {r['current_confidence']*100:.2f}%")
    print(f"Validation status:             {r['validation_status']}")
    print(f"Recommendation:                {r['advancement_recommendation']}")

if __name__ == "__main__":
    main()
