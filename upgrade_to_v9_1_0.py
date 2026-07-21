import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module35 import MODULE35_SCHEMA
from crypto_platform.module36 import MODULE36_SCHEMA
def main():
 s,_=load_all(); db=path_for(s,'database_path'); b=db.with_name(db.stem+'_before_v9_1_0'+db.suffix);
 if db.exists() and not b.exists(): shutil.copy2(db,b); print(f'Database backup: {b}')
 c=connect(s); c.execute(MODULE35_SCHEMA); c.execute(MODULE36_SCHEMA); c.close(); print('Crypto Intelligence Platform v9.1.0 installed.'); print('Modules 35 and 36 are ready.'); print('Modules 25-34 remain unchanged.')
if __name__=='__main__': main()
