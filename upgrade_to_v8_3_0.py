import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module32 import MODULE32_SCHEMA

def main():
    s,_=load_all(); db=path_for(s,"database_path")
    b=db.with_name(db.stem+"_before_v8_3_0"+db.suffix)
    if db.exists() and not b.exists(): shutil.copy2(db,b); print(f"Database backup: {b}")
    c=connect(s); c.execute(MODULE32_SCHEMA); c.close()
    print("Crypto Intelligence Platform v8.3.0 installed.")
    print("Module 32 Validation Hardening & Benchmark Intelligence is ready.")
    print("Modules 25-31 and all existing data remain unchanged.")

if __name__=="__main__":
    main()
