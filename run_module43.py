from crypto_platform.module43 import run_module43


def main():
    print("Crypto Intelligence Platform — Module 43 v43.0")
    print("Institutional Decision Intelligence\n")

    result = run_module43()

    print("Investment Committee Brief")
    print("--------------------------")
    print(
        f"Recommendation date:     "
        f"{result['recommendation_date']}"
    )
    print(
        f"Committee decision:      "
        f"{result['committee_decision']}"
    )
    print(
        f"Capital posture:         "
        f"{result['capital_posture']}"
    )
    print(
        f"Review window:           "
        f"{result['review_window']}"
    )
    print(
        f"Target crypto:           "
        f"{result['target_crypto_pct']:.2f}%"
    )
    print(
        f"Target cash:             "
        f"{result['target_cash_pct']:.2f}%"
    )
    print(
        f"Highest-ranked asset:    "
        f"{result['highest_ranked_asset']}"
    )
    print(
        f"Highest-ranked score:    "
        f"{result['highest_ranked_score']:.2f}"
    )
    print(
        f"Evidence status:         "
        f"{result['evidence_status']}"
    )
    print(
        f"Rationale:               "
        f"{result['decision_rationale']}"
    )


if __name__ == "__main__":
    main()
