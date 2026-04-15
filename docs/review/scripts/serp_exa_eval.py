"""
serp_exa_eval.py - 用 Exa 搜索 serp_skill 评测的 10 个关键词
获取每个关键词的前 10 个搜索结果，用于与 Google/Serper/Brave/Tavily 对比
"""
import json, subprocess, time, os
from urllib.parse import urlparse

EXA_API_KEY = os.getenv('EXA_API_KEY', '91241aa3-051e-4712-acfe-340929df63e5')

KEYWORDS = [
    "ElevenMusic",
    "Ideogram Layerize",
    "PixVerse C1",
    "Mureka V9",
    "DreamID-Omni",
    "FireRed Image Edit",
    "SkyReels V4",
    "wan 2.7",
    "Netflix VOID",
    "HappyHorse-1.0"
]

def extract_domain(url):
    try:
        parsed = urlparse(url)
        d = parsed.hostname or ''
        return d.replace('www.', '').lower().strip()
    except:
        return ''

def search_exa(query, num_results=10):
    """Search Exa using curl (urllib returns 403)"""
    payload = json.dumps({
        "query": query,
        "numResults": num_results,
        "type": "auto",
        "contents": {
            "highlights": {"maxCharacters": 300}
        }
    })
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "https://api.exa.ai/search",
             "-H", f"x-api-key: {EXA_API_KEY}",
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"  [ERROR] Exa: {e}")
        return []
    
    results = []
    for r in data.get('results', []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "domain": extract_domain(r.get("url", "")),
            "publishedDate": r.get("publishedDate", ""),
        })
    return results

# Google Ground Truth from the evaluation report
GOOGLE_GT = {
    "ElevenMusic": [
        "suno.com", "musicmaker.im", "elements.envato.com", "elevenlabs.io",
        "elevenlabs.io", "enlivenmusic.ai", "techcrunch.com", "elevenmusicai.io",
        "musicmaker.im", "elements.envato.com"
    ],
    "Ideogram Layerize": [
        "toolkit.artlist.io", "ideogram.ai", "chatgpt.com", "fal.ai",
        "ideogram.ai", "replicate.com", "wavespeed.ai", "artlist.io",
        "ideogram.ai", "fal.ai"
    ],
    "PixVerse C1": [
        "app.pixverse.ai", "docs.platform.pixverse.ai", "app.pixverse.ai",
        "pixverse.ai", "app.pixverse.ai", "", "", "", "", ""
    ],
    "Mureka V9": [
        "mureka.ai", "apps.apple.com", "mureka.ai",
        "play.google.com", "whatlaunched.today", "", "", "", "", ""
    ],
    "DreamID-Omni": [
        "github.com", "arxiv.org", "huggingface.co", "dreamidomni.net",
        "arxiv.org", "researchgate.net", "guoxu1233.github.io", "", "", ""
    ],
    "FireRed Image Edit": [
        "github.com", "huggingface.co", "arxiv.org", "rundown.ai",
        "fal.ai", "fireredimage.com", "comfy.org", "", "", ""
    ],
    "SkyReels V4": [
        "skyreels.ai", "arxiv.org", "huggingface.co", "skyreels.ai",
        "skyreels.org", "wavespeed.ai", "", "", "", ""
    ],
    "wan 2.7": [
        "together.ai", "create.wan.video", "wan2-7.org", "wavespeed.ai",
        "atlascloud.ai", "play.google.com", "picsart.com", "replicate.com", "", ""
    ],
    "Netflix VOID": [
        "forbes.com", "huggingface.co", "netflix.com", "marktechpost.com",
        "therecursive.com", "", "", "", "", ""
    ],
    "HappyHorse-1.0": [
        "happyhorse.app", "happyhorse.video", "wavespeed.ai", "happyhorse-ai.com",
        "x.com", "phemex.com", "reddit.com", "happyhorse.app",
        "eu.36kr.com", "happy-horse.net"
    ]
}

def main():
    all_results = {}
    
    print(f"Evaluating Exa for {len(KEYWORDS)} keywords (serp_skill scenario)...\n")
    
    for i, kw in enumerate(KEYWORDS):
        print(f"[{i+1}/{len(KEYWORDS)}] {kw}")
        results = search_exa(kw)
        all_results[kw] = results
        
        # Show top 10 domains
        domains = [r["domain"] for r in results[:10]]
        for j, d in enumerate(domains):
            print(f"  {j+1}. {d}")
        print(f"  Total: {len(results)} results")
        time.sleep(1)
    
    # Save raw data
    with open('/Users/zhangjian/project/keyword/docs/searchreview/review/exa_serp_eval.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    # Analysis: Domain overlap with Google GT
    print("\n" + "=" * 80)
    print("ANALYSIS: Exa vs Google Ground Truth")
    print("=" * 80)
    
    total_gt_domains = 0
    total_exa_overlap = 0
    total_top3_hits = 0
    total_top3_possible = 0
    
    print(f"\n{'Keyword':<25} | {'GT域名数':>8} | {'Exa重合':>8} | {'Top3命中':>8}")
    print("-" * 60)
    
    for kw in KEYWORDS:
        gt_domains = [d for d in GOOGLE_GT[kw] if d]  # remove empty
        gt_unique = set(gt_domains)
        gt_top3 = [d for d in gt_domains[:3] if d]
        
        exa_results = all_results.get(kw, [])
        exa_domains = [r["domain"] for r in exa_results[:10]]
        exa_unique = set(exa_domains)
        
        overlap = gt_unique & exa_unique
        top3_hits = sum(1 for d in gt_top3 if d in exa_unique)
        
        total_gt_domains += len(gt_unique)
        total_exa_overlap += len(overlap)
        total_top3_hits += top3_hits
        total_top3_possible += len(gt_top3)
        
        print(f"{kw:<25} | {len(gt_unique):>8} | {len(overlap):>8} | {top3_hits}/{len(gt_top3)}")
    
    print("-" * 60)
    print(f"{'TOTAL':<25} | {total_gt_domains:>8} | {total_exa_overlap:>8} ({total_exa_overlap*100//total_gt_domains}%) | {total_top3_hits}/{total_top3_possible} ({total_top3_hits*100//total_top3_possible}%)")
    
    # Show Exa Top 10 for report
    print("\n\n=== Exa Top 10 Results per Keyword (for report) ===\n")
    for kw in KEYWORDS:
        print(f"### {kw}")
        exa_results = all_results.get(kw, [])
        for j, r in enumerate(exa_results[:10]):
            print(f"  {j+1}. {r['domain']}")
        print()
    
    print(f"\n[OK] Raw data saved to docs/searchreview/review/exa_serp_eval.json")

if __name__ == "__main__":
    main()
