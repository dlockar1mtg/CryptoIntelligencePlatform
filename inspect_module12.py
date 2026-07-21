from crypto_platform.platform import load_all,connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA
from crypto_platform.module12 import MODULE12_SCHEMA
def show(c,t,q):
 print(f"\n{t}\n"+'-'*len(t)); f=c.execute(q).fetchdf(); print(f.to_string(index=False) if not f.empty else 'No data.')
def main():
 s,_=load_all(); c=connect(s)
 for x in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA,MODULE7_SCHEMA,MODULE8_SCHEMA,MODULE9_SCHEMA,MODULE10_SCHEMA,MODULE11_SCHEMA,MODULE12_SCHEMA]: c.execute(x)
 show(c,'EXACT VERIFIED SYMBOL MAP',"SELECT asset_id,provider,provider_symbol,quote_currency,market_type,mapping_method,mapping_confidence FROM latest_symbol_map ORDER BY asset_id,market_type,provider")
 show(c,'MAPPING AUDIT',"SELECT asset_id,research_symbol,provider,provider_symbol,market_type,expected_base_symbol,actual_base_symbol,actual_quote_symbol,exact_match,accepted,rejection_reason FROM latest_mapping_audit ORDER BY accepted DESC,asset_id")
 show(c,'HISTORY INTEGRITY AUDIT',"SELECT asset_id,source,invalid_epoch_rows,invalid_future_rows,duplicate_rows,rows_removed,first_valid_date,latest_valid_date FROM latest_history_integrity_audit WHERE rows_removed>0 ORDER BY rows_removed DESC")
 show(c,'DATA INTEGRITY SUMMARY',"SELECT asset_id,verified_spot_providers,verified_perpetual_providers,history_days,history_coverage_pct,invalid_rows_removed,derivatives_supported,integrity_status FROM latest_data_integrity_summary ORDER BY integrity_status,history_coverage_pct DESC")
 show(c,'VERIFIED DERIVATIVES STATUS',"SELECT asset_id,provider_symbol,supported,funding_rows,open_interest_rows,status,error_message FROM latest_derivatives_status WHERE provider_symbol<>'UNMAPPED' ORDER BY supported DESC,asset_id")
 show(c,'LATEST MODULE 12 RUNS',"SELECT * FROM module12_runs ORDER BY started_at_utc DESC LIMIT 10")
 c.close()
if __name__=='__main__': main()
