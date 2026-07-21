from crypto_platform.module42 import run_module42


def main():
    print("Crypto Intelligence Platform — Module 42 v42.0")
    print("Investment Decision & Long-Range Projection Engine\n")

    result = run_module42()

    print("Module 42 summary")
    print("-----------------")
    print(
        f"Recommendation date:       "
        f"{result['recommendation_date']}"
    )
    print(
        f"Overall action:            "
        f"{result['overall_action']}"
    )
    print(
        f"Overall timeline:          "
        f"{result['overall_timeline']}"
    )
    print(
        f"Target crypto weight:      "
        f"{result['target_risk_weight']*100:.2f}%"
    )
    print(
        f"Target cash weight:        "
        f"{result['target_cash_weight']*100:.2f}%"
    )
    print(
        f"Highest-conviction asset:  "
        f"{result['highest_conviction_asset']}"
    )
    print(
        f"Highest-conviction score:  "
        f"{result['highest_conviction_score']:.2f}"
    )
    print(
        f"Positive-action assets:    "
        f"{int(result['positive_assets'])}"
    )
    print(
        f"Wait/hold assets:          "
        f"{int(result['wait_assets'])}"
    )
    print(
        f"Reduce/avoid assets:       "
        f"{int(result['reduce_assets'])}"
    )
    print(
        f"Evidence status:           "
        f"{result['evidence_status']}"
    )
    print(
        f"Decision status:           "
        f"{result['decision_status']}"
    )


if __name__ == "__main__":
    main()
