from crypto_platform.platform import load_all,connect
from crypto_platform.module39 import MODULE39_SCHEMA

def main():
    s,_=load_all();c=connect(s);c.execute(MODULE39_SCHEMA)
    count=c.execute("SELECT COUNT(*) FROM information_schema.columns WHERE lower(table_name)='module39_runs'").fetchone()[0]
    c.close()
    assert count==19,count
    print("v10.1.1 Module 39 schema preflight passed.")
    print(f"module39_runs columns: {count}")

if __name__=="__main__":main()
