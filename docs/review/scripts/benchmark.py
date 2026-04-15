"""
Search Engine Benchmark: Brave vs Serper vs Tavily
Compare competitor discovery capability across 3 search APIs.
"""
import sqlite3, requests, json, time, random, os, sys
from urllib.parse import urlparse
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, 'e:/getbacklink')
from dotenv import load_dotenv
load_dotenv('e:/getbacklink/.env')

# ── Config ────────────────────────────────────────────────────────────────────
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
HTTP_PROXY = os.getenv('HTTP_PROXY', '')
PROXIES = {"http": HTTP_PROXY, "https": HTTP_PROXY} if HTTP_PROXY else None

PAGES = 5  # 5 pages x 10 = 50 results per engine

def extract_domain(url):
    try:
        parsed = urlparse(url)
        d = parsed.hostname or ''
        return d.replace('www.', '').lower().strip()
    except:
        return ''

# ── Database: Get 10 random keywords ─────────────────────────────────────────
conn = sqlite3.connect('e:/getbacklink/data/tasks.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT keyword FROM keywords 
    WHERE created_at >= date('now', '-1 day', '+8 hours')
    AND status = 'active'
    ORDER BY RANDOM() 
    LIMIT 10
""")
keywords = [r['keyword'] for r in c.fetchall()]
conn.close()

if len(keywords) < 10:
    # fallback: get any recent active keywords
    conn = sqlite3.connect('e:/getbacklink/data/tasks.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT keyword FROM keywords WHERE status='active' ORDER BY RANDOM() LIMIT 10")
    keywords = [r['keyword'] for r in c.fetchall()]
    conn.close()

print(f"Selected {len(keywords)} keywords for benchmark")
for i, kw in enumerate(keywords):
    print(f"  {i+1}. {kw}")

# ── Search Functions ──────────────────────────────────────────────────────────
def search_serper(keyword, pages=PAGES):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    results = []
    seen = set()
    for page in range(1, pages + 1):
        payload = {'q': keyword, 'num': 10, 'page': page, 'gl': 'us', 'hl': 'en'}
        try:
            resp = requests.post('https://google.serper.dev/search', headers=headers,
                                 json=payload, timeout=30, proxies=PROXIES)
            if resp.status_code == 200:
                for item in resp.json().get('organic', []):
                    link = item.get('link', '')
                    if link not in seen:
                        seen.add(link)
                        results.append({'title': item.get('title', ''), 
                                       'snippet': item.get('snippet', ''), 'link': link})
            else:
                print(f"  Serper error page {page}: {resp.status_code}")
                break
        except Exception as e:
            print(f"  Serper exception: {e}")
            break
        if page < pages: time.sleep(0.5)
    return results

def search_brave(keyword, pages=PAGES):
    headers = {'Accept': 'application/json', 'X-Subscription-Token': BRAVE_API_KEY}
    results = []
    seen = set()
    # Brave API: offset = page number (0-9), count = results per page (max 20)
    # Use count=10, offset=0~(pages-1) to get pages*10 results
    for page_offset in range(0, min(pages, 10)):
        params = {'q': keyword, 'count': 10, 'offset': page_offset, 'country': 'US', 'search_lang': 'en'}
        try:
            resp = requests.get('https://api.search.brave.com/res/v1/web/search', headers=headers,
                                params=params, timeout=30, proxies=PROXIES)
            if resp.status_code == 200:
                web_results = resp.json().get('web', {}).get('results', [])
                if not web_results:
                    break
                for item in web_results:
                    link = item.get('url', '')
                    if link not in seen:
                        seen.add(link)
                        results.append({'title': item.get('title', ''),
                                       'snippet': item.get('description', ''), 'link': link})
            else:
                print(f"  Brave error (offset={page_offset}): {resp.status_code} {resp.text[:100]}")
                break
        except Exception as e:
            print(f"  Brave exception: {e}")
            break
        time.sleep(1)
    return results

def search_tavily(keyword, pages=PAGES):
    headers = {'Content-Type': 'application/json'}
    max_results = pages * 10
    payload = {'api_key': TAVILY_API_KEY, 'query': keyword, 'search_depth': 'advanced', 'max_results': max_results}
    results = []
    try:
        resp = requests.post('https://api.tavily.com/search', headers=headers,
                             json=payload, timeout=45, proxies=PROXIES)
        if resp.status_code == 200:
            seen = set()
            for item in resp.json().get('results', []):
                link = item.get('url', '')
                if link and link not in seen:
                    seen.add(link)
                    results.append({'title': item.get('title', ''),
                                   'snippet': item.get('content', '')[:150], 'link': link})
        else:
            print(f"  Tavily error: {resp.status_code}")
    except Exception as e:
        print(f"  Tavily exception: {e}")
    return results

# ── Noise domains (directories, aggregators, etc.) ─────────────────────────
NOISE_DOMAINS = {
    'reddit.com', 'quora.com', 'youtube.com', 'github.com', 'wikipedia.org',
    'twitter.com', 'x.com', 'facebook.com', 'linkedin.com', 'instagram.com',
    'medium.com', 'tiktok.com', 'amazon.com', 'apple.com', 'google.com',
    'toolify.ai', 'theresanaiforthat.com', 'futurepedia.io', 'producthunt.com',
    'g2.com', 'capterra.com', 'alternativeto.net', 'stackshare.io',
    'crunchbase.com', 'trustpilot.com', 'sitejabber.com',
}

AI_KEYWORDS = {'ai', 'artificial intelligence', 'machine learning', 'deep learning', 
               'generative', 'neural', 'gpt', 'llm', 'automated', 'intelligent'}

def is_potential_competitor(result):
    """Heuristic: does this result look like an AI SaaS product?"""
    domain = extract_domain(result['link'])
    if domain in NOISE_DOMAINS:
        return False
    text = f"{result['title']} {result['snippet']}".lower()
    return any(kw in text for kw in AI_KEYWORDS)

# ── Run Benchmark ─────────────────────────────────────────────────────────────
all_data = {}  # keyword -> {engine -> results}

for i, kw in enumerate(keywords):
    print(f"\n[{i+1}/{len(keywords)}] Searching: {kw}")
    all_data[kw] = {}
    
    # Serper
    print("  -> Serper...", end=" ", flush=True)
    serper_res = search_serper(kw)
    all_data[kw]['serper'] = serper_res
    print(f"{len(serper_res)} results")
    
    time.sleep(0.5)
    
    # Brave
    print("  -> Brave...", end=" ", flush=True)
    brave_res = search_brave(kw)
    all_data[kw]['brave'] = brave_res
    print(f"{len(brave_res)} results")
    
    time.sleep(0.5)
    
    # Tavily
    print("  -> Tavily...", end=" ", flush=True)
    tavily_res = search_tavily(kw)
    all_data[kw]['tavily'] = tavily_res
    print(f"{len(tavily_res)} results")
    
    time.sleep(1)

# ── Analyze ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

engines = ['serper', 'brave', 'tavily']
stats = {e: {'total': 0, 'unique_domains': set(), 'ai_relevant': 0, 'competitor_domains': set()} for e in engines}

keyword_details = {}  # for report

for kw, engine_results in all_data.items():
    kw_stats = {}
    for engine in engines:
        results = engine_results.get(engine, [])
        domains = set()
        ai_count = 0
        comp_domains = set()
        for r in results:
            d = extract_domain(r['link'])
            if d: domains.add(d)
            if is_potential_competitor(r):
                ai_count += 1
                if d: comp_domains.add(d)
        
        stats[engine]['total'] += len(results)
        stats[engine]['unique_domains'].update(domains)
        stats[engine]['ai_relevant'] += ai_count
        stats[engine]['competitor_domains'].update(comp_domains)
        
        kw_stats[engine] = {
            'count': len(results),
            'domains': len(domains),
            'ai_count': ai_count,
            'comp_domains': comp_domains,
            'results': results[:5]  # top 5 for report
        }
    keyword_details[kw] = kw_stats

# ── Save raw data ─────────────────────────────────────────────────────────────
with open('e:/getbacklink/review/benchmark_raw.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)
print("Raw data saved to review/benchmark_raw.json")

# ── Generate Report ───────────────────────────────────────────────────────────
report = []
report.append(f"# Search Engine Benchmark Report")
report.append(f"")
report.append(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
report.append(f"- **Model**: Claude Opus 4.6")
report.append(f"- **Keywords tested**: {len(keywords)}")
report.append(f"- **Pages per engine**: {PAGES} (max ~{PAGES*10} results)")
report.append(f"")
report.append(f"---")
report.append(f"")

# Conclusion
report.append(f"## Summary")
report.append(f"")
report.append(f"| Metric | Serper | Brave | Tavily |")
report.append(f"|---|---|---|---|")
report.append(f"| Total results | {stats['serper']['total']} | {stats['brave']['total']} | {stats['tavily']['total']} |")
report.append(f"| Unique domains | {len(stats['serper']['unique_domains'])} | {len(stats['brave']['unique_domains'])} | {len(stats['tavily']['unique_domains'])} |")
report.append(f"| AI-relevant hits | {stats['serper']['ai_relevant']} | {stats['brave']['ai_relevant']} | {stats['tavily']['ai_relevant']} |")
report.append(f"| Potential competitor domains | {len(stats['serper']['competitor_domains'])} | {len(stats['brave']['competitor_domains'])} | {len(stats['tavily']['competitor_domains'])} |")
report.append(f"")

# Auto-determine winner
ai_scores = {e: stats[e]['ai_relevant'] for e in engines}
domain_scores = {e: len(stats[e]['competitor_domains']) for e in engines}
best_ai = max(ai_scores, key=ai_scores.get)
best_domain = max(domain_scores, key=domain_scores.get)

report.append(f"**Winner by AI-relevant results**: **{best_ai.upper()}** ({ai_scores[best_ai]} hits)")
report.append(f"")
report.append(f"**Winner by unique competitor domains**: **{best_domain.upper()}** ({domain_scores[best_domain]} domains)")
report.append(f"")
report.append(f"---")
report.append(f"")

# Per-keyword breakdown
report.append(f"## Per-Keyword Breakdown")
report.append(f"")
report.append(f"| Keyword | Serper (total/AI) | Brave (total/AI) | Tavily (total/AI) |")
report.append(f"|---|---|---|---|")
for kw, kw_stats in keyword_details.items():
    s = kw_stats['serper']
    b = kw_stats['brave']
    t = kw_stats['tavily']
    report.append(f"| {kw[:40]} | {s['count']}/{s['ai_count']} | {b['count']}/{b['ai_count']} | {t['count']}/{t['ai_count']} |")
report.append(f"")

# Overlap analysis
report.append(f"## Domain Overlap Analysis")
report.append(f"")
s_dom = stats['serper']['competitor_domains']
b_dom = stats['brave']['competitor_domains']
t_dom = stats['tavily']['competitor_domains']
all_comp = s_dom | b_dom | t_dom
only_serper = s_dom - b_dom - t_dom
only_brave = b_dom - s_dom - t_dom
only_tavily = t_dom - s_dom - b_dom
shared_all = s_dom & b_dom & t_dom

report.append(f"| Category | Count | Domains |")
report.append(f"|---|---|---|")
report.append(f"| All 3 engines | {len(shared_all)} | {', '.join(sorted(shared_all)[:10])} |")
report.append(f"| Serper only | {len(only_serper)} | {', '.join(sorted(only_serper)[:10])} |")
report.append(f"| Brave only | {len(only_brave)} | {', '.join(sorted(only_brave)[:10])} |")
report.append(f"| Tavily only | {len(only_tavily)} | {', '.join(sorted(only_tavily)[:10])} |")
report.append(f"| Total unique | {len(all_comp)} | - |")
report.append(f"")

# Sample results table
report.append(f"## Sample Search Results (Top 3 per engine per keyword)")
report.append(f"")
for kw, kw_stats in keyword_details.items():
    report.append(f"### `{kw}`")
    report.append(f"")
    report.append(f"| Engine | # | Domain | Title | AI? |")
    report.append(f"|---|---|---|---|---|")
    for engine in engines:
        results = kw_stats[engine].get('results', [])[:3]
        for j, r in enumerate(results):
            d = extract_domain(r['link'])
            is_ai = 'Y' if is_potential_competitor(r) else ''
            title = r['title'][:50]
            report.append(f"| {engine} | {j+1} | {d} | {title} | {is_ai} |")
    report.append(f"")

report_text = "\n".join(report)

with open('e:/getbacklink/review/search_benchmark_report.md', 'w', encoding='utf-8') as f:
    f.write(report_text)

print(f"\nReport saved to review/search_benchmark_report.md")
print(f"Total unique AI competitor domains found: {len(all_comp)}")
