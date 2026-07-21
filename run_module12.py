from crypto_platform.module12 import run_module12
def main():
    print("Crypto Intelligence Platform — Module 12 v12.0")
    print("Exact mapping, timestamp integrity, history repair, and verified derivatives\n")
    r=run_module12()
    print("Module 12 summary\n-----------------")
    for label,key in [("Status","status"),("Mappings verified","mappings_verified"),("Mappings rejected","mappings_rejected"),("Invalid rows removed","invalid_rows_removed"),("History rows repaired","history_rows_repaired"),("Derivative rows","derivatives_rows"),("Universe assets removed","universe_rows_removed"),("Integrity summary rows","summary_rows"),("Run ID","run_id")]: print(f"{label:25} {r[key]}")
if __name__=='__main__': main()
