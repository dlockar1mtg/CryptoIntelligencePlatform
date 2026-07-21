from crypto_platform.module11 import run_module11

def main():
    print("Crypto Intelligence Platform — Module 11 v11.0")
    print("Provider mapping, resilient history, derivatives repair, taxonomy, and robust calibration\n")
    result = run_module11()
    print("Module 11 summary")
    print("-----------------")
    print(f"Status:                   {result['status']}")
    print(f"Mapped assets:            {result['mapped_assets']}")
    print(f"Mapping rows:             {result['mapping_rows']}")
    print(f"Historical rows:          {result['history_rows']}")
    print(f"History quality rows:     {result['quality_rows']}")
    print(f"Derivative rows:          {result['derivatives_rows']}")
    print(f"Taxonomy rows:            {result['taxonomy_rows']}")
    print(f"Sector rows:              {result['sector_rows']}")
    print(f"Calibrated predictions:   {result['calibrated_predictions']}")
    print(f"Run ID:                   {result['run_id']}")

if __name__ == "__main__":
    main()
