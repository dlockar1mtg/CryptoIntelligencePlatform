from crypto_platform.platform import load_all,connect
from crypto_platform.module35 import MODULE35_SCHEMA
from crypto_platform.module36 import MODULE36_SCHEMA
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE35_SCHEMA); c.execute(MODULE36_SCHEMA); a=c.execute("SELECT COUNT(*) FROM information_schema.columns WHERE lower(table_name)='module35_runs'").fetchone()[0]; b=c.execute("SELECT COUNT(*) FROM information_schema.columns WHERE lower(table_name)='module36_runs'").fetchone()[0]; c.close(); assert a==19,(a,b); assert b==20,(a,b); print('v9.1.0 schema preflight passed.'); print({'module35_runs':a,'module36_runs':b})
if __name__=='__main__': main()
