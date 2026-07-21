from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module41 import MODULE41_SCHEMA

EXPORTS={
"latest_m41_meta_summary":"SELECT * FROM latest_m41_meta_summary",
"latest_m41_adaptive_model_weights":"SELECT * FROM latest_m41_adaptive_model_weights",
"latest_m41_horizon_reliability":"SELECT * FROM latest_m41_horizon_reliability",
"latest_m41_confidence_adjustments":"SELECT * FROM latest_m41_confidence_adjustments",
"latest_m41_optimizer_feedback":"SELECT * FROM latest_m41_optimizer_feedback",
"latest_m41_retraining_plan":"SELECT * FROM latest_m41_retraining_plan",
"module41_runs":"SELECT * FROM module41_runs",
}

def main():
    s,_=load_all();c=connect(s);c.execute(MODULE41_SCHEMA)
    d=path_for(s,"export_directory");d.mkdir(parents=True,exist_ok=True)
    for n,q in EXPORTS.items():
        f=c.execute(q).fetchdf();p=d/f"{n}.csv";f.to_csv(p,index=False)
        print(f"{n}: {len(f)} rows -> {p}")
    c.close()

if __name__=="__main__":main()
