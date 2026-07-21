from __future__ import annotations
import argparse
from crypto_platform.module6 import run_module6

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", choices=["all", "sync", "research"], default="all"
    )
    args = parser.parse_args()
    print("Crypto Intelligence Platform — Module 6 v6.0")
    print("Historical warehouse, model snapshots, and validation\n")
    result = run_module6(args.phase)
    print("Module 6 summary")
    print("----------------")
    print(f"Status:               {result['status']}")
    print(f"Phase:                {result['phase']}")
    print(f"Canonical rows:       {result['canonical_rows']}")
    print(f"Snapshots created:    {result['snapshots_created']}")
    print(f"Validations created:  {result['validations_created']}")
    print(f"Run ID:               {result['run_id']}")

if __name__ == "__main__":
    main()
