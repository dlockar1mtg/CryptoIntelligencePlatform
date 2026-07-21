from crypto_platform.module41 import run_module41

def main():
    print("Crypto Intelligence Platform — Module 41 v41.0")
    print("Adaptive Meta-Learning Engine\n")
    r=run_module41()
    print("Module 41 summary")
    print("-----------------")
    print(f"Adaptive model rows:       {int(r['adaptive_models'])}")
    print(f"Asset/horizon rows:        {int(r['asset_horizons'])}")
    print(f"Matured forecasts:         {int(r['matured_forecasts'])}")
    print(f"Evidence ratio:            {r['evidence_ratio']:.2%}")
    print(f"Mean reliability score:    {r['mean_reliability_score']:.2f}")
    print(f"Mean confidence change:    {r['mean_confidence_change']:.4f}")
    print(f"High-priority models:      {int(r['high_priority_models'])}")
    print(f"Meta-learning status:      {r['meta_learning_status']}")
    print(f"Recommendation:            {r['advancement_recommendation']}")

if __name__=="__main__":main()
