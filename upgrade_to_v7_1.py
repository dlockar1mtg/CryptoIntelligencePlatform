import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module26 import MODULE26_SCHEMA
def main():
 s,_=load_all(); db=path_for(s,'database_path'); b=db.with_name(db.stem+'_before_v7_1'+db.suffix)
 if db.exists() and not b.exists(): shutil.copy2(db,b); print(f'Database backup: {b}')
 c=connect(s); c.execute(MODULE26_SCHEMA); c.close(); print('Crypto Intelligence Platform v7.1 installed.'); print('Module 26 Adaptive Regime Research Engine is ready.'); print('Module 25 classifications remain unchanged.')
if __name__=='__main__': main()
