from crypto_platform.module5 import run_module5

def main():
    print("Crypto Intelligence Platform — Module 5 v5.0")
    print("Multi-horizon returns, cycle analytics, expected returns, and risk optimization\n")
    result = run_module5()
    print("Module 5 summary")
    print("----------------")
    print(f"Status:           {result['status']}")
    print(f"Signal date:      {result['signal_date']}")
    print(f"Assets analyzed:  {result['assets_analyzed']}")
    print(f"Run ID:           {result['run_id']}")

if __name__ == "__main__":
    main()
