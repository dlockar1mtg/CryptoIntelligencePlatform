from crypto_platform.module19 import run_module19

def main():
    print("Crypto Intelligence Platform — Module 19 v19.0")
    print("Research promotion, rolling validation, and feature registry\n")
    result = run_module19()
    print("Module 19 summary")
    print("-----------------")
    print(
        f"Status:                       {result['status']}"
    )
    print(
        "Refreshed validation rows:    "
        f"{result['refreshed_validation_rows']}"
    )
    print(
        "Rolling validation rows:      "
        f"{result['rolling_validation_rows']}"
    )
    print(
        "Grouped permutation rows:     "
        f"{result['grouped_permutation_rows']}"
    )
    print(
        f"Registry rows:                {result['registry_rows']}"
    )
    print(
        f"Promoted shadow features:     {result['promoted_features']}"
    )
    print(
        f"Demoted features:             {result['demoted_features']}"
    )
    print(
        f"Run ID:                       {result['run_id']}"
    )

if __name__ == "__main__":
    main()
