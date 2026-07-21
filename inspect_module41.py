from crypto_platform.platform import load_all,connect
from crypto_platform.module41 import MODULE41_SCHEMA

def show(c,t,q):
    print(f"\n{t}\n{'-'*len(t)}")
    f=c.execute(q).fetchdf()
    print(f.to_string(index=False) if not f.empty else "No data.")

def main():
    s,_=load_all();c=connect(s);c.execute(MODULE41_SCHEMA)
    show(c,"META SUMMARY","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m41_meta_summary")
    show(c,"ADAPTIVE MODEL WEIGHTS","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m41_adaptive_model_weights")
    show(c,"HORIZON RELIABILITY","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m41_horizon_reliability")
    show(c,"CONFIDENCE ADJUSTMENTS","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m41_confidence_adjustments")
    show(c,"OPTIMIZER FEEDBACK","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m41_optimizer_feedback")
    show(c,"RETRAINING PLAN","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m41_retraining_plan")
    show(c,"LATEST RUNS","SELECT * FROM module41_runs ORDER BY started_at_utc DESC LIMIT 10")
    c.close()

if __name__=="__main__":main()
