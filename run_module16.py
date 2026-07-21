from crypto_platform.module16 import run_module16

def main():
 print("Crypto Intelligence Platform — Module 16 v16.0")
 print("Candidate generation, caching, optimization, and research rankings\n")
 r=run_module16()
 print("Module 16 summary")
 print("-----------------")
 print(f"Status:                 {r['status']}")
 print(f"Candidates evaluated:   {r['candidate_count']}")
 print(f"Cached results reused:  {r['cached_count']}")
 print(f"Shortlist size:         {r['shortlist_count']}")
 print(f"Walk-forward complete:  {r['walk_forward_count']}")
 print(f"Best candidate:         {r['best_candidate_id']}")
 print(f"Best robust score:      {r['best_robust_score']:.2f}")
 print(f"Promotion status:       {r['promotion_status']}")
 print(f"Experiment ID:          {r['experiment_id']}")
if __name__=='__main__':main()
