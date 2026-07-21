import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module18 import MODULE18_SCHEMA
def main():
    s,_=load_all(); db=path_for(s,'database_path'); backup=db.with_name(db.stem+'_before_v4_2_1'+db.suffix)
    if db.exists() and not backup.exists(): shutil.copy2(db,backup); print(f'Database backup: {backup}')
    c=connect(s); c.execute(MODULE18_SCHEMA); c.close()
    print('Crypto Intelligence Platform v4.2.1 installed.')
    print('Live Module 13 scoring remains unchanged.')
if __name__=='__main__': main()
