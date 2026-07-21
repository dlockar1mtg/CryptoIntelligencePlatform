from crypto_platform.module26 import run_module26
def main():
 print('Crypto Intelligence Platform — Module 26 v26.0\nAdaptive Regime Research Engine\n'); r=run_module26()
 print('Module 26 summary\n-----------------')
 for label,key,fmt in [('Candidate features','candidate_features','d'),('Selected features','selected_features','d'),('Outer folds','outer_folds','d'),('Nested test rows','nested_test_rows','d'),('Nested agreement','nested_agreement_pct','.2f'),('Raw calibration MAE','raw_calibration_mae','.4f'),('Calibrated MAE','calibrated_mae','.4f'),('Sensitivity stability','sensitivity_stability_pct','.2f')]:
  v=r[key]; print(f'{label+":":30} {int(v) if fmt=="d" else format(v,fmt)}')
 print(f"Current research regime:       {r['current_regime']}")
 print(f"Current calibrated confidence: {r['current_confidence']*100:.2f}%")
 print(f"Validation status:             {r['validation_status']}")
 print(f"Recommendation:                {r['advancement_recommendation']}")
if __name__=='__main__': main()
