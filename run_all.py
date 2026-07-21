from crypto_platform.platform import run_module1
from crypto_platform.module2 import run_module2
from crypto_platform.module3 import run_module3
from crypto_platform.module5 import run_module5
from crypto_platform.module6 import run_module6
from crypto_platform.module7 import run_module7
from crypto_platform.module8 import run_module8
from crypto_platform.module9 import run_module9
from crypto_platform.module10 import run_module10
from crypto_platform.module11 import run_module11
from crypto_platform.module12 import run_module12
from crypto_platform.module13 import run_module13
from crypto_platform.module14 import run_module14
from crypto_platform.module15 import run_module15
from crypto_platform.module16 import run_module16
from crypto_platform.module17 import run_module17

def main():
    print("Running Crypto Module 1...")
    m1 = run_module1(False)
    print(f"Module 1: {m1['status']}")

    print("\nSynchronizing deep historical warehouse...")
    sync = run_module6("sync")
    print(f"Canonical historical rows: {sync['canonical_rows']}")

    print("\nRunning Crypto Module 2...")
    m2 = run_module2()
    print(f"Module 2: {m2['status']}")
    print(f"Macro regime: {m2['macro_regime']}")
    print(f"Market regime: {m2['market_regime']}")

    print("\nRunning Crypto Module 3...")
    m3 = run_module3()
    print(f"Module 3: {m3['status']}")
    print(f"Recommended monthly: ${m3['monthly_contribution_usd']:,.2f}")

    print("\nRunning Crypto Module 5...")
    m5 = run_module5()
    print(f"Module 5: {m5['status']}")

    print("\nBuilding historical research and validation...")
    m6 = run_module6("research")
    print(f"Module 6: {m6['status']}")
    print(f"Snapshots: {m6['snapshots_created']}")

    print("\nRunning rules-model calibration...")
    m7 = run_module7()
    print(f"Module 7: {m7['status']}")
    print(f"Calibration samples: {m7['calibration_samples']}")

    print("\nRunning predictive intelligence...")
    m8 = run_module8()
    print(f"Module 8: {m8['status']}")
    print(f"ML ensemble weight: {m8['ml_weight']:.1%}")
    print(f"ML promoted: {m8['promoted']}")
    print(f"Predictions: {m8['prediction_count']}")

    print("\nRunning calibrated predictive decisions...")
    m9 = run_module9()
    print(f"Module 9: {m9['status']}")
    print(f"Walk-forward folds: {m9['validation_folds']}")
    print(f"Predictive weight: {m9['predictive_weight']:.1%}")
    print(f"Predictive model promoted: {m9['promoted']}")

    print("\nRunning institutional data expansion...")
    m10 = run_module10()
    print(f"Module 10: {m10['status']}")
    print(f"Research universe: {m10['selected_assets']} assets")
    print(f"History rows: {m10['history_rows']}")
    print(f"Calibrated predictions: {m10['calibrated_predictions']}")

    print("\nRunning data reliability and taxonomy upgrades...")
    m11 = run_module11()
    print(f"Module 11: {m11['status']}")
    print(f"Mapped assets: {m11['mapped_assets']}")
    print(f"Historical rows: {m11['history_rows']}")
    print(f"Derivative rows: {m11['derivatives_rows']}")
    print(f"Taxonomy rows: {m11['taxonomy_rows']}")

    print("\nRunning data integrity release...")
    m12 = run_module12()
    print(f"Module 12: {m12['status']}")
    print(f"Verified mappings: {m12['mappings_verified']}")
    print(f"Invalid rows removed: {m12['invalid_rows_removed']}")
    print(f"History rows repaired: {m12['history_rows_repaired']}")
    print(f"Derivative rows: {m12['derivatives_rows']}")

    print("\nRunning market structure and recommendation engine...")
    m13=run_module13()
    print(f"Module 13: {m13['status']}")
    print(f"Assets analyzed: {m13['assets_analyzed']}")
    print(f"Recommendations: {m13['recommendations']}")
    print(f"Derivatives provider: {m13['derivatives_provider']}")

    print("\nRunning scoring and portfolio validation...")
    m14 = run_module14()
    print(f"Module 14: {m14['status']}")
    print(f"Rebalance periods: {m14['rebalance_periods']}")
    print(f"Excess return: {m14['excess_return_pct']:.2f}%")
    print(f"Methodology promoted: {m14['promoted']}")

    print("\nRunning research and calibration engine...")
    m15 = run_module15()
    print(f"Module 15: {m15['status']}")
    print(f"Selected variant: {m15['selected_variant']}")
    print(f"OOS excess return: {m15['oos_excess_pct']:.2f}%")
    print(f"Promotion candidate: {m15['promoted']}")

    print("\nRunning optimization framework...")
    m16=run_module16()
    print(f"Module 16: {m16['status']}")
    print(f"Best candidate: {m16['best_candidate_id']}")
    print(f"Promotion status: {m16['promotion_status']}")

    print("\nRunning feature expansion...")
    m17 = run_module17()
    print(f"Module 17: {m17['status']}")
    print(f"Feature rows: {m17['feature_rows']}")
    print(f"Research-ready features: {m17['ready_features']}")

if __name__ == "__main__":
    main()
