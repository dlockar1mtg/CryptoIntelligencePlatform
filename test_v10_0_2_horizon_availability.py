def adaptive_split(
    usable_rows,
    configured_validation=120,
    absolute_minimum=90,
    minimum_validation=30,
    maximum_validation_share=0.25,
):
    validation = min(
        configured_validation,
        max(
            minimum_validation,
            int(
                usable_rows
                * maximum_validation_share
            ),
        ),
    )
    validation = min(
        validation,
        usable_rows - absolute_minimum,
    )
    training = usable_rows - validation
    return training, validation


def main():
    training_7d, validation_7d = adaptive_split(328)
    assert (training_7d, validation_7d) == (246, 82)

    training_180d, validation_180d = adaptive_split(155)
    assert training_180d == 117
    assert validation_180d == 38
    assert training_180d >= 90
    assert validation_180d >= 30

    training_short, validation_short = adaptive_split(80)
    assert training_short < 90 or validation_short < 30

    print("v10.0.2 horizon-availability smoke test passed.")
    print(
        f"7-day example: training={training_7d}, "
        f"validation={validation_7d}"
    )
    print(
        f"180-day example: training={training_180d}, "
        f"validation={validation_180d}"
    )
    print("Insufficient combinations will be skipped safely.")


if __name__ == "__main__":
    main()
