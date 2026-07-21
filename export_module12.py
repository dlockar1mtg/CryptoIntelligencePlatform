from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module12 import MODULE12_SCHEMA
EXPORTS={'exchange_metadata_assets':'SELECT * FROM exchange_metadata_assets','exchange_metadata_markets':'SELECT * FROM exchange_metadata_markets','latest_mapping_audit':'SELECT * FROM latest_mapping_audit','symbol_mapping_audit':'SELECT * FROM symbol_mapping_audit','latest_history_integrity_audit':'SELECT * FROM latest_history_integrity_audit','history_integrity_audit':'SELECT * FROM history_integrity_audit','latest_data_integrity_summary':'SELECT * FROM latest_data_integrity_summary','data_integrity_summary':'SELECT * FROM data_integrity_summary','module12_runs':'SELECT * FROM module12_runs'}
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE12_SCHEMA); d=path_for(s,'export_directory'); d.mkdir(parents=True,exist_ok=True)
 for n,q in EXPORTS.items():
  f=c.execute(q).fetchdf(); p=d/f'{n}.csv'; f.to_csv(p,index=False); print(f'{n}: {len(f)} rows -> {p}')
 c.close()
if __name__=='__main__': main()
