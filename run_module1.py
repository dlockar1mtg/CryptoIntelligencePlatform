from __future__ import annotations
import argparse
from crypto_platform.platform import run_module1

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-refresh", action="store_true")
    args = parser.parse_args()

    print("Crypto Intelligence Platform — Module 1 v2.0")
    print("Provider-aware data collection\n")
    result = run_module1(args.full_refresh)

    print("\nCollection summary")
    print("------------------")
    print(f"Successful collectors: {result['successful_collectors']}")
    print(f"Failed collectors:     {result['failed_collectors']}")
    print(f"Rows received:         {result['received']}")
    print(f"Rows inserted:         {result['inserted']}")
    print(f"Rows updated:          {result['updated']}")
    print(f"Status:                {result['status']}")
    print(f"Database:              {result['database_path']}")
    print(f"Run ID:                {result['run_id']}")

if __name__ == "__main__":
    main()
