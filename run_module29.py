from crypto_platform.module29 import run_module29


def main():
    print("Crypto Intelligence Platform — Module 29 v29.0")
    print("Explainable AI Research Framework\n")

    result = run_module29()

    print("Module 29 summary")
    print("-----------------")
    print(
        f"Candidate features:             "
        f"{int(result['candidate_features'])}"
    )
    print(
        f"Stable features:                "
        f"{int(result['stable_features'])}"
    )
    print(
        f"Stable core features:           "
        f"{int(result['stable_core_features'])}"
    )
    print(
        f"Stable representation features: "
        f"{int(result['stable_representation_features'])}"
    )
    print(
        f"Full-feature accuracy:          "
        f"{result['full_feature_accuracy_pct']:.2f}%"
    )
    print(
        f"Core-only accuracy:             "
        f"{result['core_only_accuracy_pct']:.2f}%"
    )
    print(
        f"Stable-feature accuracy:        "
        f"{result['stable_feature_accuracy_pct']:.2f}%"
    )
    print(
        f"Stable worst fold:              "
        f"{result['stable_feature_worst_fold_pct']:.2f}%"
    )
    print(
        f"Bootstrap iterations:           "
        f"{int(result['bootstrap_iterations'])}"
    )
    print(
        f"Rolling windows:                "
        f"{int(result['rolling_windows'])}"
    )
    print(
        f"Validation status:              "
        f"{result['validation_status']}"
    )
    print(
        f"Recommendation:                 "
        f"{result['advancement_recommendation']}"
    )


if __name__ == "__main__":
    main()
