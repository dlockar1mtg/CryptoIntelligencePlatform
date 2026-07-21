from crypto_platform.module35 import run_module35
def main():
 print('Crypto Intelligence Platform — Module 35 v35.0\nPortfolio Construction Engine\n'); r=run_module35();
 for k,v in r.items():
  if k not in {'run_id','calculated_at_utc','observation_date'}: print(f'{k}: {v}')
if __name__=='__main__': main()
