from crypto_platform.module28 import run_module28

def main():
    print("Crypto Intelligence Platform — Module 28 v28.0")
    print("Feature Selection & Adaptive Optimization\n")
    r=run_module28()
    print("Module 28 summary")
    print("-----------------")
    print(f"Candidate features:              {int(r['candidate_features'])}")
    print(f"Retained features:               {int(r['retained_features'])}")
    print(f"Adaptive candidates per fold:    {int(r['adaptive_candidates'])}")
    print(f"Outer folds:                     {int(r['outer_folds'])}")
    print(f"Nested test rows:                {int(r['nested_rows'])}")
    print(f"Nested agreement:                {r['nested_agreement_pct']:.2f}%")
    print(f"Raw calibration MAE:             {r['raw_calibration_mae']:.4f}")
    print(f"Calibrated MAE:                  {r['calibrated_mae']:.4f}")
    print(f"Meta-ensemble stability:         {r['meta_ensemble_stability_pct']:.2f}%")
    print(f"Current research regime:         {r['current_regime']}")
    print(f"Current calibrated confidence:   {r['current_confidence']*100:.2f}%")
    print(f"Validation status:               {r['validation_status']}")
    print(f"Recommendation:                  {r['advancement_recommendation']}")

if __name__=="__main__":
    main()
