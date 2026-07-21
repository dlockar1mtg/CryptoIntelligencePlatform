import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module20 import MODULE20_SCHEMA
def main():
    s,_=load_all();db=path_for(s,'database_path');b=db.with_name(db.stem+'_before_v4_2_3'+db.suffix)
    if db.exists() and not b.exists():shutil.copy2(db,b);print(f'Database backup: {b}')
    c=connect(s);c.execute(MODULE20_SCHEMA);c.close();print('Crypto Intelligence Platform v4.2.3 installed.');print('Research maturity and shadow validation are ready.');print('Live Module 13 scoring remains unchanged.')
if __name__=='__main__':main()
