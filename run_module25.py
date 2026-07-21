from crypto_platform.module25 import run_module25

def main():
    print("Crypto Intelligence Platform — Module 25 v25.0")
    print("Adaptive Market Regime Intelligence\n")

    result = run_module25()

    print("Module 25 summary")
    print("-----------------")
    print(f"Status:                     {result['status']}")
    print(f"Feature rows:               {result['feature_rows']}")
    print(f"Classified days:            {result['classified_days']}")
    print(f"Transition rows:            {result['transitions']}")
    print(f"Duration rows:              {result['duration_rows']}")
    print(f"Current regime:             {result['current_regime']}")
    print(f"Secondary regime:           {result['secondary_regime']}")
    print(
        "Current confidence:         "
        f"{result['current_confidence']*100:.2f}%"
    )
    print(f"Days in regime:             {result['days_in_regime']}")
    print(
        "Expected persistence:       "
        f"{result['expected_persistence_days']:.1f} days"
    )
    print(
        "Transition risk:            "
        f"{result['transition_risk']*100:.2f}%"
    )
    print(
        "Reproducibility match:      "
        f"{result['reproducibility_match_pct']:.2f}%"
    )
    print(
        "Stability score:            "
        f"{result['stability_score']:.2f}"
    )
    print(
        f"Validation status:          {result['validation_status']}"
    )
    print(f"Run ID:                     {result['run_id']}")

if __name__ == "__main__":
    main()
