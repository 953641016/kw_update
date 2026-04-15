import json
from urllib.parse import urlparse

def get_domain(url):
    try:
        if not url: return ""
        netloc = urlparse(url).netloc
        return netloc.lower().replace("www.", "")
    except: return ""

def analyze():
    with open("data/search_snapshots.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    report = {}

    for kw, engines in data.items():
        google_domains = [get_domain(res.get("url") or res.get("link")) for res in engines.get("Local_Google", [])]
        google_domains = [d for d in google_domains if d]
        
        kw_metrics = {}
        for engine_name in ["Serper", "Brave", "Tavily"]:
            results = engines.get(engine_name, [])
            engine_domains = [get_domain(res.get("url") or res.get("link")) for res in results]
            engine_domains = [d for d in engine_domains if d]
            
            # 1. Overlap with Google (unique domains)
            overlap = set(google_domains) & set(engine_domains)
            
            # 2. Heuristic: Is a "product-like" domain present?
            # Looking for domains that appear in Google top 3 or have keywords in them
            top_google = google_domains[:3]
            found_top_google = any(d in engine_domains for d in top_google)
            
            kw_metrics[engine_name] = {
                "overlap_count": len(overlap),
                "found_top_google": found_top_google,
                "domains": list(dict.fromkeys(engine_domains))[:5] # Top 5 domains for quick check
            }
        
        report[kw] = kw_metrics

    # Aggregate
    summary = {"Serper": 0, "Brave": 0, "Tavily": 0}
    for kw in report:
        for eng in summary:
            summary[eng] += report[kw][eng]["overlap_count"]

    print("### Search API Analysis Summary")
    print(f"{'Engine':<10} | {'Total Overlap':<15}")
    print("-" * 30)
    for eng, count in summary.items():
        print(f"{eng:<10} | {count:<15}")
    
    with open("data/analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    analyze()
