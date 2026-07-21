import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module28 import MODULE28_SCHEMA

def main():
    settings,_=load_all()
    database=path_for(settings,"database_path")
    backup=database.with_name(
        database.stem+"_before_v7_3"+database.suffix
    )
    if database.exists() and not backup.exists():
        shutil.copy2(database,backup)
        print(f"Database backup: {backup}")
    conn=connect(settings)
    conn.execute(MODULE28_SCHEMA)
    conn.close()
    print("Crypto Intelligence Platform v7.3 installed.")
    print("Module 28 Feature Selection & Adaptive Optimization is ready.")
    print("Modules 25-27 remain unchanged.")

if __name__=="__main__":
    main()
