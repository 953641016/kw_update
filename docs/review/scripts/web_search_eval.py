"""
web_search_eval.py - 评测 4 个搜索 API 在 openclaw web_search 信息补全场景中的表现
场景 A：关键词精化（官方写法确权、噪声补偿、repo 名转换）
场景 B：站内搜索降级（site: 限定搜索 fallback）
"""
import json, subprocess, time, os, sys
from urllib.parse import urlparse
from datetime import datetime

EXA_API_KEY = os.getenv('EXA_API_KEY', '91241aa3-051e-4712-acfe-340929df63e5')

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts', '.env'))
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

import requests

# ── Test Queries ──────────────────────────────────────────────────────────────

QUERIES = [
    # 场景 A：关键词精化
    {"id": "A1", "category": "official_name", "query": "Seedance 2.0 official",
     "desc": "热门产品词确权", "expect_domains": ["seed.bytedance.com", "seedance2.ai", "huggingface.co"]},
    {"id": "A2", "category": "official_name", "query": "DreamID-Omni official",
     "desc": "学术技术词确权", "expect_domains": ["github.com", "arxiv.org", "huggingface.co"]},
    {"id": "A3", "category": "noise_detect", "query": "HiAR",
     "desc": "Trends噪声检测（美发品牌污染）", "expect_domains": []},
    {"id": "A4", "category": "repo_to_keyword", "query": "AnimateDiff-Lightning",
     "desc": "GitHub repo名→搜索词", "expect_domains": ["github.com", "huggingface.co"]},
    {"id": "A5", "category": "repo_to_keyword", "query": "Wan-2.2-T2V-A14B",
     "desc": "HF repo名→产品搜索词", "expect_domains": ["huggingface.co", "github.com"]},
    {"id": "A6", "category": "official_name", "query": "TADA TTS official",
     "desc": "冷门学术词确权", "expect_domains": ["github.com", "arxiv.org"]},
    # 场景 B：站内搜索降级
    {"id": "B1", "category": "site_search", "query": "site:youtube.com AI video generator tutorial 2026",
     "desc": "YouTube fallback", "expect_site": "youtube.com",
     "exa_domain": "youtube.com"},
    {"id": "B2", "category": "site_search", "query": "site:venturebeat.com AI model release 2026",
     "desc": "VentureBeat fallback", "expect_site": "venturebeat.com",
     "exa_domain": "venturebeat.com"},
    {"id": "B3", "category": "site_search", "query": "site:producthunt.com AI video image generator launched",
     "desc": "ProductHunt fallback", "expect_site": "producthunt.com",
     "exa_domain": "producthunt.com"},
    {"id": "B4", "category": "site_search", "query": "site:reddit.com r/StableDiffusion new model release",
     "desc": "Reddit fallback", "expect_site": "reddit.com",
     "exa_domain": "reddit.com"},
    {"id": "B5", "category": "site_search", "query": "site:x.com AI model release announcement 2026",
     "desc": "X/Twitter fallback", "expect_site": "x.com",
     "exa_domain": "x.com"},
    {"id": "B6", "category": "site_search", "query": 'site:zhihu.com "Seedance 2.0" 使用体验',
     "desc": "知乎中文搜索", "expect_site": "zhihu.com",
     "exa_domain": "zhihu.com"},
]

def extract_domain(url):
    try:
        parsed = urlparse(url)
        d = parsed.hostname or ''
        return d.replace('www.', '').lower().strip()
    except:
        return ''

# ── Search Functions ──────────────────────────────────────────────────────────

def search_serper(query, num=5):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = {'q': query, 'num': num, 'gl': 'us', 'hl': 'en'}
    try:
        resp = requests.post('https://google.serper.dev/search', headers=headers,
                             json=payload, timeout=15)
        if resp.status_code == 200:
            results = []
            for item in resp.json().get('organic', [])[:num]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'domain': extract_domain(item.get('link', '')),
                    'snippet': item.get('snippet', '')[:150],
                })
            return results
        else:
            print(f"  Serper error: {resp.status_code}")
    except Exception as e:
        print(f"  Serper exception: {e}")
    return []

def search_brave(query, num=5):
    headers = {'Accept': 'application/json', 'X-Subscription-Token': BRAVE_API_KEY}
    params = {'q': query, 'count': num, 'country': 'US', 'search_lang': 'en'}
    try:
        resp = requests.get('https://api.search.brave.com/res/v1/web/search', headers=headers,
                            params=params, timeout=15)
        if resp.status_code == 200:
            results = []
            for item in resp.json().get('web', {}).get('results', [])[:num]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'domain': extract_domain(item.get('url', '')),
                    'snippet': item.get('description', '')[:150],
                })
            return results
        else:
            print(f"  Brave error: {resp.status_code}")
    except Exception as e:
        print(f"  Brave exception: {e}")
    return []

def search_tavily(query, num=5):
    headers = {'Content-Type': 'application/json'}
    payload = {'api_key': TAVILY_API_KEY, 'query': query, 'search_depth': 'basic', 'max_results': num}
    try:
        resp = requests.post('https://api.tavily.com/search', headers=headers,
                             json=payload, timeout=20)
        if resp.status_code == 200:
            results = []
            for item in resp.json().get('results', [])[:num]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'domain': extract_domain(item.get('url', '')),
                    'snippet': item.get('content', '')[:150],
                })
            return results
        else:
            print(f"  Tavily error: {resp.status_code}")
    except Exception as e:
        print(f"  Tavily exception: {e}")
    return []

def search_exa(query, num=5, include_domain=None):
    """Exa search via curl (urllib returns 403)"""
    payload = {
        "query": query.replace("site:", ""),  # Exa 不支持 site: 语法
        "numResults": num,
        "type": "auto",
        "contents": {
            "highlights": {"maxCharacters": 300}
        }
    }
    if include_domain:
        payload["includeDomains"] = [include_domain]
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "https://api.exa.ai/search",
             "-H", f"x-api-key: {EXA_API_KEY}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"  Exa exception: {e}")
        return []
    
    results = []
    for r in data.get('results', [])[:num]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "domain": extract_domain(r.get("url", "")),
            "snippet": "",
        })
    return results

# ── Main Evaluation ──────────────────────────────────────────────────────────

def main():
    all_results = {}
    
    print(f"信息补全场景评测：{len(QUERIES)} 条查询 × 4 个 API")
    print("=" * 80)
    
    for i, q in enumerate(QUERIES):
        qid = q["id"]
        query = q["query"]
        print(f"\n[{i+1}/{len(QUERIES)}] {qid}: {q['desc']}")
        print(f"  Query: {query}")
        
        all_results[qid] = {"query": query, "desc": q["desc"], "category": q["category"]}
        
        # Serper
        print("  -> Serper...", end=" ", flush=True)
        serper = search_serper(query)
        all_results[qid]["serper"] = serper
        print(f"{len(serper)} results")
        
        time.sleep(0.3)
        
        # Brave
        print("  -> Brave...", end=" ", flush=True)
        brave = search_brave(query)
        all_results[qid]["brave"] = brave
        print(f"{len(brave)} results")
        
        time.sleep(0.5)
        
        # Tavily
        print("  -> Tavily...", end=" ", flush=True)
        tavily = search_tavily(query)
        all_results[qid]["tavily"] = tavily
        print(f"{len(tavily)} results")
        
        time.sleep(0.3)
        
        # Exa (use includeDomains for site: queries)
        print("  -> Exa...", end=" ", flush=True)
        exa_domain = q.get("exa_domain")
        exa = search_exa(query, include_domain=exa_domain)
        all_results[qid]["exa"] = exa
        print(f"{len(exa)} results")
        
        time.sleep(0.5)
    
    # Save raw data
    output_dir = os.path.dirname(os.path.abspath(__file__))
    raw_file = os.path.join(output_dir, 'web_search_eval.json')
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n原始数据已保存: {raw_file}")
    
    # ── Analysis ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    apis = ["serper", "brave", "tavily", "exa"]
    
    # Scene A: Official source hit rate
    print("\n=== 场景 A：关键词精化 ===\n")
    scene_a_queries = [q for q in QUERIES if q["category"] != "site_search"]
    
    print(f"{'ID':<5} {'描述':<25} | {'Serper':<20} | {'Brave':<20} | {'Tavily':<20} | {'Exa':<20}")
    print("-" * 115)
    
    for q in scene_a_queries:
        qid = q["id"]
        row = f"{qid:<5} {q['desc']:<25} |"
        for api in apis:
            results = all_results[qid].get(api, [])
            if results:
                top1 = results[0]["domain"]
                row += f" {top1:<19}|"
            else:
                row += f" {'(empty)':<19}|"
        print(row)
    
    # Scene A: detailed top3 per query
    print("\n--- 场景 A 详细 Top3 ---\n")
    for q in scene_a_queries:
        qid = q["id"]
        print(f"\n{qid}: {q['query']}")
        for api in apis:
            results = all_results[qid].get(api, [])
            domains = [r["domain"] for r in results[:3]]
            print(f"  {api:>7}: {' → '.join(domains) if domains else '(empty)'}")
    
    # Scene B: site: operator compliance
    print("\n\n=== 场景 B：站内搜索降级（site: 支持） ===\n")
    scene_b_queries = [q for q in QUERIES if q["category"] == "site_search"]
    
    print(f"{'ID':<5} {'目标站点':<20} | {'Serper':>7} | {'Brave':>7} | {'Tavily':>7} | {'Exa':>7}")
    print("-" * 70)
    
    for q in scene_b_queries:
        qid = q["id"]
        target = q["expect_site"]
        row = f"{qid:<5} {target:<20} |"
        for api in apis:
            results = all_results[qid].get(api, [])
            if not results:
                row += f" {'0/0':>7} |"
                continue
            on_site = sum(1 for r in results if target in r["domain"])
            total = len(results)
            row += f" {on_site}/{total}:>7 |"
        print(row)
    
    # Scene B: detailed
    print("\n--- 场景 B 详细 Top5 域名 ---\n")
    for q in scene_b_queries:
        qid = q["id"]
        target = q["expect_site"]
        print(f"\n{qid}: {q['query']}")
        print(f"  目标: {target}")
        for api in apis:
            results = all_results[qid].get(api, [])
            domains = [r["domain"] for r in results[:5]]
            compliance = all(target in d for d in domains) if domains else False
            marker = "✅" if compliance else "⚠️"
            print(f"  {api:>7} {marker}: {' | '.join(domains) if domains else '(empty)'}")
    
    print(f"\n[OK] 评测完成。数据保存: {raw_file}")

if __name__ == "__main__":
    main()
