import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module25_validation import MODULE25V_SCHEMA
def main():
    s,_=load_all(); db=path_for(s,"database_path")
    b=db.with_name(db.stem+"_before_v7_0_3"+db.suffix)
    if db.exists() and not b.exists(): shutil.copy2(db,b); print(f"Database backup: {b}")
    c=connect(s); c.execute(MODULE25V_SCHEMA); c.close()
    print("Crypto Intelligence Platform v7.0.3 installed.")
    print("Module 25V Regime Validation & Robustness is ready.")
if __name__=="__main__": main()
