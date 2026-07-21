from crypto_platform.module23 import run_module23
def main():
 print('Crypto Intelligence Platform — Module 23 v23.0')
 print('Backtest validation, independent accounting, and promotion audit\n')
 r=run_module23()
 print('Module 23 summary')
 print('-----------------')
 for k,label in [('status','Status'),('source_module22_run_id','Source Module 22 run'),('periods_audited','Periods audited'),('critical_findings','Critical findings'),('warning_findings','Warning findings'),('stored_return_pct','Stored return'),('corrected_return_pct','Corrected return %'),('btc_return_pct','Bitcoin return %'),('corrected_excess_pct','Corrected excess %'),('audit_status','Audit status'),('promotion_status','Promotion status'),('run_id','Run ID')]: print(f'{label}: {r[k]}')
 print(f"Bootstrap P(excess > 0): {r['bootstrap_probability_excess_positive']*100:.2f}%")
if __name__=='__main__': main()
