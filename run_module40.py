from crypto_platform.module40 import run_module40


def main():
    print("Crypto Intelligence Platform — Module 40 v40.0")
    print("Forecast Memory & Continuous Learning\n")

    result = run_module40()

    print("Module 40 summary")
    print("-----------------")
    print(
        f"Forecasts stored:             "
        f"{int(result['forecasts_stored'])}"
    )
    print(
        f"Pending forecasts:            "
        f"{int(result['pending_forecasts'])}"
    )
    print(
        f"Matured forecasts:            "
        f"{int(result['matured_forecasts'])}"
    )
    print(
        f"Assets tracked:               "
        f"{int(result['assets_tracked'])}"
    )
    print(
        f"Horizons tracked:             "
        f"{int(result['horizons_tracked'])}"
    )
    print(
        f"Mean absolute error:          "
        f"{result['mean_absolute_error_pct']}"
    )
    print(
        f"Directional accuracy:         "
        f"{result['directional_accuracy_pct']}"
    )
    print(
        f"Mean Brier score:             "
        f"{result['mean_brier_score']}"
    )
    print(
        f"Interval coverage:            "
        f"{result['interval_coverage_pct']}"
    )
    print(
        f"High-priority retraining:     "
        f"{int(result['high_priority_retraining_rows'])}"
    )
    print(
        f"Memory status:                "
        f"{result['memory_status']}"
    )
    print(
        f"Continuous learning:          "
        f"{result['continuous_learning_status']}"
    )
    print(
        f"Recommendation:               "
        f"{result['advancement_recommendation']}"
    )


if __name__ == "__main__":
    main()
