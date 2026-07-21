from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module34 import MODULE34_SCHEMA

EXPORTS={
"latest_m34_validation_summary":"SELECT * FROM latest_m34_validation_summary",
"latest_m34_execution_candidates":"SELECT * FROM latest_m34_execution_candidates",
"latest_m34_execution_daily":"SELECT * FROM latest_m34_execution_daily",
"latest_m34_trade_ledger":"SELECT * FROM latest_m34_trade_ledger",
"latest_m34_execution_drift":"SELECT * FROM latest_m34_execution_drift",
"latest_m34_cost_sensitivity":"SELECT * FROM latest_m34_cost_sensitivity",
"latest_m34_benchmark_summary":"SELECT * FROM latest_m34_benchmark_summary",
"module34_runs":"SELECT * FROM module34_runs",
}

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE34_SCHEMA)
    d=path_for(s,"export_directory"); d.mkdir(parents=True,exist_ok=True)
    for n,q in EXPORTS.items():
        f=c.execute(q).fetchdf(); p=d/f"{n}.csv"; f.to_csv(p,index=False)
        print(f"{n}: {len(f)} rows -> {p}")
    c.close()

if __name__=="__main__":
    main()
