from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module25_validation import MODULE25V_SCHEMA
EXPORTS={
"latest_m25v_validation_summary":"SELECT * FROM latest_m25v_validation_summary",
"latest_m25v_walk_forward_regimes":"SELECT * FROM latest_m25v_walk_forward_regimes",
"latest_m25v_event_window_audit":"SELECT * FROM latest_m25v_event_window_audit",
"latest_m25v_regime_asset_performance":"SELECT * FROM latest_m25v_regime_asset_performance",
"latest_m25v_module13_regime_audit":"SELECT * FROM latest_m25v_module13_regime_audit",
"latest_m25v_probability_calibration":"SELECT * FROM latest_m25v_probability_calibration",
"latest_m25v_parameter_sensitivity":"SELECT * FROM latest_m25v_parameter_sensitivity",
"module25v_runs":"SELECT * FROM module25v_runs",
}
def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE25V_SCHEMA)
    d=path_for(s,"export_directory"); d.mkdir(parents=True,exist_ok=True)
    for n,q in EXPORTS.items():
        f=c.execute(q).fetchdf(); p=d/f"{n}.csv"; f.to_csv(p,index=False); print(f"{n}: {len(f)} rows -> {p}")
    c.close()
if __name__=="__main__": main()
