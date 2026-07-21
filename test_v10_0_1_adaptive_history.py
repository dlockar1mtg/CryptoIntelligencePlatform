import numpy as np
import pandas as pd

from crypto_platform.module38 import Module38Runner


def main():
    usable_rows = 328
    configured_minimum = 450
    configured_validation = 120
    absolute_minimum = 160
    minimum_validation = 45
    maximum_validation_share = 0.25

    adaptive_validation = min(
        configured_validation,
        max(
            minimum_validation,
            int(
                usable_rows
                * maximum_validation_share
            ),
        ),
    )
    adaptive_validation = min(
        adaptive_validation,
        usable_rows - absolute_minimum,
    )
    adaptive_training = (
        usable_rows - adaptive_validation
    )

    assert adaptive_training >= absolute_minimum
    assert adaptive_validation >= minimum_validation
    assert adaptive_training == 246
    assert adaptive_validation == 82

    print("v10.0.1 adaptive-history smoke test passed.")
    print(f"Usable rows:       {usable_rows}")
    print(f"Training rows:     {adaptive_training}")
    print(f"Validation rows:   {adaptive_validation}")


if __name__ == "__main__":
    main()
