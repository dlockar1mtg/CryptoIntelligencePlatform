import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module34 import MODULE34_SCHEMA

def main():
    s,_=load_all(); db=path_for(s,"database_path")
    b=db.with_name(db.stem+"_before_v8_4_0"+db.suffix)
    if db.exists() and not b.exists():
        shutil.copy2(db,b); print(f"Database backup: {b}")
    c=connect(s); c.execute(MODULE34_SCHEMA); c.close()
    print("Crypto Intelligence Platform v8.4.0 installed.")
    print("Module 34 Institutional Portfolio Execution Engine is ready.")
    print("Modules 25-33 and all existing data remain unchanged.")

if __name__=="__main__":
    main()
