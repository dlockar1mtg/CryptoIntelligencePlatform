import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module31 import MODULE31_SCHEMA
def main():
 s,_=load_all(); db=path_for(s,'database_path'); b=db.with_name(db.stem+'_before_v8_2'+db.suffix)
 if db.exists() and not b.exists(): shutil.copy2(db,b); print(f'Database backup: {b}')
 c=connect(s); c.execute(MODULE31_SCHEMA); c.close()
 print('Crypto Intelligence Platform v8.2 installed.')
 print('Module 31 Research Validation is ready.')
 print('Module 30 remains OBSERVATION only.')
if __name__=='__main__': main()
