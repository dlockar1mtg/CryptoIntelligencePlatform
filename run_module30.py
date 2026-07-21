from crypto_platform.module30 import run_module30


def main():
    print("Crypto Intelligence Platform — Module 30 v30.1")
    print("Clean Regime Engine\n")

    result = run_module30()

    print("Module 30 summary")
    print("-----------------")
    print(f"Status:                  {result['status']}")
    print(f"Stable features:         {result['stable_features']}")
    print(f"Outer folds:             {result['outer_folds']}")
    print(f"Historical test rows:    {result['historical_rows']}")
    print(
        f"Clean accuracy:          "
        f"{result['clean_accuracy_pct']:.2f}%"
    )
    print(
        f"Clean log loss:          "
        f"{result['clean_log_loss']:.4f}"
    )
    print(
        f"Clean Brier score:       "
        f"{result['clean_brier_score']:.4f}"
    )
    print(f"Current regime:          {result['current_regime']}")
    print(f"Secondary regime:        {result['secondary_regime']}")
    print(
        f"Current probability:     "
        f"{result['current_probability']*100:.2f}%"
    )
    print(f"Confidence level:        {result['confidence_level']}")
    print(
        f"Model agreement:         "
        f"{result['model_agreement']*100:.2f}%"
    )
    print(f"Feature drift:           {result['drift_status']}")
    print(f"Legacy regime:           {result['legacy_regime']}")
    print(f"Validation status:       {result['validation_status']}")
    print(f"Promotion status:        {result['promotion_status']}")
    print(f"Experiment ID:           {result['experiment_id']}")
    print(f"Run ID:                  {result['run_id']}")


if __name__ == "__main__":
    main()
