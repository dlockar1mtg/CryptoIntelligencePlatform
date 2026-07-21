from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module28 import MODULE28_SCHEMA

EXPORTS={
"latest_m28_research_summary":"SELECT * FROM latest_m28_research_summary",
"latest_m28_feature_selection":"SELECT * FROM latest_m28_feature_selection",
"latest_m28_adaptive_search":"SELECT * FROM latest_m28_adaptive_search",
"latest_m28_nested_predictions":"SELECT * FROM latest_m28_nested_predictions",
"latest_m28_calibration_comparison":"SELECT * FROM latest_m28_calibration_comparison",
"latest_m28_fold_summary":"SELECT * FROM latest_m28_fold_summary",
"latest_m28_robustness_summary":"SELECT * FROM latest_m28_robustness_summary",
"module28_runs":"SELECT * FROM module28_runs",
}

def main():
    settings,_=load_all()
    conn=connect(settings)
    conn.execute(MODULE28_SCHEMA)
    directory=path_for(settings,"export_directory")
    directory.mkdir(parents=True,exist_ok=True)
    for name,sql in EXPORTS.items():
        frame=conn.execute(sql).fetchdf()
        output=directory/f"{name}.csv"
        frame.to_csv(output,index=False)
        print(f"{name}: {len(frame)} rows -> {output}")
    conn.close()

if __name__=="__main__":
    main()
