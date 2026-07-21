import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module23 import MODULE23_SCHEMA
def main():
 s,_=load_all(); db=path_for(s,'database_path'); b=db.with_name(db.stem+'_before_v5_1_1'+db.suffix)
 if db.exists() and not b.exists(): shutil.copy2(db,b); print(f'Database backup: {b}')
 c=connect(s); c.execute(MODULE23_SCHEMA); c.close(); print('Crypto Intelligence Platform v5.1.1 installed.'); print('Module 23 audit supersedes the Module 22 promotion flag.')
if __name__=='__main__':main()
