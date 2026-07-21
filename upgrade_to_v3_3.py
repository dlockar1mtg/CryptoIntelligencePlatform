import shutil
from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module13 import MODULE13_SCHEMA
def main():
 s,_=load_all(); db=path_for(s,"database_path")
 if db.exists():
  b=db.with_name(db.stem+"_before_v3_3"+db.suffix)
  if not b.exists(): shutil.copy2(db,b); print(f"Database backup: {b}")
 c=connect(s); c.execute(MODULE13_SCHEMA)
 c.execute("UPDATE module12_runs SET status='FAILED',completed_at_utc=CURRENT_TIMESTAMP WHERE status='RUNNING'")
 c.close()
 print("Crypto Intelligence Platform v3.3 installed.")
 print("Market structure, recommendations, optional derivatives fallback, and portfolio targets are ready.")
if __name__=="__main__":main()
