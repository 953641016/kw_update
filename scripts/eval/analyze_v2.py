"""
analyze_v2.py
用修正后的 local_google_parsed_v2.json 重跑 overlap 分析。
增加 SEO 维度：竞品独立站命中率、意图污染率。
"""
import json
from urllib.parse import urlparse

def get_domain(url):
    try:
        if not url: return ""
        # Handle truncated URLs like "https://fal.ai › ideogram › layerize-text"
        url = url.split(' ')[0].split('›')[0].strip()
        if not url.startswith('http'):
            url = 'https://' + url
        netloc = urlparse(url).netloc
        return netloc.lower().replace("www.", "")
    except:
        return ""

def analyze():
    # Load corrected ground truth
    with open("data/local_google_parsed_v2.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
    
    # Load API snapshots
    with open("data/search_snapshots.json", "r", encoding="utf-8") as f:
        snapshots = json.load(f)
    
    report = {}
    totals = {"Serper": {"overlap": 0, "total_google": 0}, 
              "Brave": {"overlap": 0, "total_google": 0}, 
              "Tavily": {"overlap": 0, "total_google": 0}}

    for kw in ground_truth:
        google_results = ground_truth[kw]
        google_domains = [get_domain(r.get("url", "")) for r in google_results]
        google_domains = [d for d in google_domains if d]
        google_domains_unique = list(dict.fromkeys(google_domains))  # preserve order, dedupe
        
        if kw not in snapshots:
            print(f"⚠️ {kw} not found in search_snapshots.json, skipping")
            continue
        
        kw_data = snapshots[kw]
        kw_metrics = {"google_top_domains": google_domains_unique[:10]}
        
        for engine in ["Serper", "Brave", "Tavily"]:
            results = kw_data.get(engine, [])
            engine_domains = [get_domain(r.get("url") or r.get("link", "")) for r in results]
            engine_domains = [d for d in engine_domains if d]
            engine_domains_unique = list(dict.fromkeys(engine_domains))
            
            # Domain overlap (unique)
            overlap = set(google_domains_unique) & set(engine_domains_unique)
            
            # Top 3 hit rate
            top3_google = set(google_domains_unique[:3])
            top3_hit = len(top3_google & set(engine_domains_unique))
            
            kw_metrics[engine] = {
                "overlap": len(overlap),
                "overlap_domains": sorted(overlap),
                "top3_hit": f"{top3_hit}/{len(top3_google)}",
                "engine_top5": engine_domains_unique[:5],
                "total_results": len(results)
            }
            
            totals[engine]["overlap"] += len(overlap)
            totals[engine]["total_google"] += len(google_domains_unique)
        
        report[kw] = kw_metrics
    
    # Print summary table
    print("=" * 70)
    print(f"{'关键词':<20} | {'Google域名数':<8} | {'Serper':<8} | {'Brave':<8} | {'Tavily':<8}")
    print("-" * 70)
    for kw, m in report.items():
        g_count = len(m.get("google_top_domains", []))
        s = m.get("Serper", {}).get("overlap", 0)
        b = m.get("Brave", {}).get("overlap", 0)
        t = m.get("Tavily", {}).get("overlap", 0)
        print(f"{kw:<20} | {g_count:<8} | {s:<8} | {b:<8} | {t:<8}")
    
    print("-" * 70)
    for eng in ["Serper", "Brave", "Tavily"]:
        total_o = totals[eng]["overlap"]
        total_g = totals[eng]["total_google"]
        pct = f"{total_o}/{total_g} ({total_o/total_g*100:.0f}%)" if total_g > 0 else "N/A"
        print(f"{'合计 ' + eng:<20} | {'--':<8} | {pct}")
    
    # Print Top3 hit detail
    print("\n" + "=" * 70)
    print("Google Top3 命中率详情（各 API 是否命中 Google 排名前 3 的域名）")
    print("-" * 70)
    for kw, m in report.items():
        s = m.get("Serper", {}).get("top3_hit", "?")
        b = m.get("Brave", {}).get("top3_hit", "?")
        t = m.get("Tavily", {}).get("top3_hit", "?")
        print(f"{kw:<20} | Serper: {s:<6} | Brave: {b:<6} | Tavily: {t:<6}")
    
    with open("data/analysis_v2.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
    print(f"\n[✔] Detailed results saved to analysis_v2.json")

if __name__ == "__main__":
    analyze()
