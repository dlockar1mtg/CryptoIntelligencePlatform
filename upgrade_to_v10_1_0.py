import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module39 import MODULE39_SCHEMA

def main():
    s,_=load_all();db=path_for(s,"database_path")
    b=db.with_name(db.stem+"_before_v10_1_0"+db.suffix)
    if db.exists() and not b.exists():shutil.copy2(db,b);print(f"Database backup: {b}")
    c=connect(s);c.execute(MODULE39_SCHEMA);c.close()
    print("Crypto Intelligence Platform v10.1.0 installed.")
    print("Module 39 Forecast Calibration & Live Validation is ready.")
    print("Modules 25-38 and all existing data remain unchanged.")

if __name__=="__main__":main()
