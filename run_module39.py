from crypto_platform.module39 import run_module39

def main():
    print("Crypto Intelligence Platform — Module 39 v39.0")
    print("Forecast Calibration & Live Validation\n")
    r=run_module39()
    print("Module 39 summary")
    print("-----------------")
    print(f"Calibrated forecasts:          {int(r['calibrated_forecasts'])}")
    print(f"Calibration improved:          {r['calibration_improved_pct']:.2f}%")
    print(f"Mean calibrated Brier:         {r['mean_calibrated_brier']:.4f}")
    print(f"Mean interval coverage:        {r['mean_interval_coverage_pct']:.2f}%")
    print(f"Mean directional accuracy:     {r['mean_directional_accuracy_pct']:.2f}%")
    print(f"Stable features:               {r['stable_feature_pct']:.2f}%")
    print(f"Current forecast drift:        {r['current_drift_status']}")
    print(f"Realized scorecards available: {int(r['scorecards_available'])}")
    print(f"Validation status:             {r['validation_status']}")
    print(f"Recommendation:                {r['advancement_recommendation']}")

if __name__=="__main__":main()
