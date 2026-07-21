from crypto_platform.module36 import run_module36
def main():
 print('Crypto Intelligence Platform — Module 36 v36.0\nRisk Management Engine\n'); r=run_module36();
 for k,v in r.items():
  if k not in {'run_id','calculated_at_utc','observation_date'}: print(f'{k}: {v}')
if __name__=='__main__': main()
