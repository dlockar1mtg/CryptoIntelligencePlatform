from crypto_platform.module8 import run_module8

def main():
    print("Crypto Intelligence Platform — Module 8 v8.0")
    print("Predictive ML, SHAP explanations, regime validation, and ensemble\n")
    result = run_module8()
    print("Module 8 summary")
    print("----------------")
    print(f"Status:                 {result['status']}")
    print(f"Training rows:          {result['training_rows']}")
    print(f"Walk-forward folds:     {result['validation_folds']}")
    print(f"Recommended ML weight:  {result['ml_weight']:.1%}")
    print(f"Promoted:               {result['promoted']}")
    print(f"Current predictions:    {result['prediction_count']}")
    print(f"SHAP explanations:      {result['explanation_count']}")
    print(f"Model artifact:         {result['model_artifact_path']}")
    print(f"Run ID:                 {result['run_id']}")

if __name__ == "__main__":
    main()
