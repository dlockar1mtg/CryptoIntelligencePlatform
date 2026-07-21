import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module16 import MODULE16_SCHEMA

def main():
 s,_=load_all();db=path_for(s,'database_path')
 if db.exists():
  b=db.with_name(db.stem+'_before_v4_1_0'+db.suffix)
  if not b.exists():shutil.copy2(db,b);print(f'Database backup: {b}')
 c=connect(s);c.execute(MODULE16_SCHEMA);c.close()
 print('Crypto Intelligence Platform v4.1.0 installed.')
 print('Module 16 optimization framework is ready.')
 print('The live Module 13 methodology remains unchanged.')
if __name__=='__main__':main()
