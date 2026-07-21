import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module12 import MODULE12_SCHEMA
def main():
 s,_=load_all(); db=path_for(s,'database_path')
 if db.exists():
  b=db.with_name(db.stem+'_before_v3_2'+db.suffix)
  if not b.exists(): shutil.copy2(db,b); print(f'Database backup: {b}')
 c=connect(s); c.execute(MODULE12_SCHEMA); c.execute("UPDATE module11_runs SET status='FAILED',completed_at_utc=CURRENT_TIMESTAMP WHERE status='RUNNING'"); c.close(); print('Crypto Intelligence Platform v3.2 installed.'); print('Modules 1-11 and valid existing data were preserved.')
if __name__=='__main__': main()
