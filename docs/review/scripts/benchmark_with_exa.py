"""
Search Engine Benchmark: Brave vs Serper vs Tavily vs Exa
Compare competitor discovery capability across 4 search APIs.
"""
import requests, json, time, os, sys
from urllib.parse import urlparse
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
EXA_API_KEY = os.getenv('EXA_API_KEY', '91241aa3-051e-4712-acfe-340929df63e5')
HTTP_PROXY = os.getenv('HTTP_PROXY', '')
PROXIES = {"http": HTTP_PROXY, "https": HTTP_PROXY} if HTTP_PROXY else None

PAGES = 5  # 5 pages x 10 = 50 results per engine

# Test keywords from the original benchmark
KEYWORDS = [
    "ai song creator",
    "ai song creation tool",
    "ai content creation tool",
    "ai design platform",
    "ai voice recognition",
    "ai video editor",
    "educational voice generator",
    "generative video software",
    "video editing ai",
    "realistic voice generator"
]

RESULTS_PER_KEYWORD = 50  # 每个关键词50条结果

def extract_domain(url):
    try:
        parsed = urlparse(url)
        d = parsed.hostname or ''
        return d.replace('www.', '').lower().strip()
    except:
        return ''

# ── Search Functions ──────────────────────────────────────────────────────────

def search_serper(keyword, pages=PAGES):
    """Google搜索结果 via Serper API"""
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
    """Brave Search API"""
    headers = {'Accept': 'application/json', 'X-Subscription-Token': BRAVE_API_KEY}
    results = []
    seen = set()
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
    """Tavily AI Search API"""
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

def search_exa(keyword, num_results=RESULTS_PER_KEYWORD):
    """Exa AI Search API - 语义搜索"""
    headers = {'x-api-key': EXA_API_KEY, 'Content-Type': 'application/json'}
    
    payload = {
        'query': keyword,
        'type': 'auto',  # 平衡相关性和速度
        'num_results': num_results,
        'contents': {
            'highlights': {'max_characters': 4000}
        }
    }
    
    results = []
    try:
        resp = requests.post('https://api.exa.ai/search', headers=headers,
                             json=payload, timeout=60, proxies=PROXIES)
        if resp.status_code == 200:
            data = resp.json()
            seen = set()
            for item in data.get('results', []):
                link = item.get('url', '')
                if link and link not in seen:
                    seen.add(link)
                    # Exa 返回高亮内容，取第一个作为 snippet
                    highlights = item.get('highlights', [])
                    snippet = highlights[0] if highlights else item.get('text', '')[:150]
                    results.append({
                        'title': item.get('title', ''),
                        'snippet': snippet[:150] if snippet else '',
                        'link': link
                    })
        else:
            print(f"  Exa error: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"  Exa exception: {e}")
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
    """启发式判断：这个结果是否看起来像 AI SaaS 产品？"""
    domain = extract_domain(result['link'])
    if domain in NOISE_DOMAINS:
        return False
    text = f"{result['title']} {result['snippet']}".lower()
    return any(kw in text for kw in AI_KEYWORDS)

# ── Run Exa Benchmark Only ────────────────────────────────────────────────────
all_data = {}  # keyword -> {exa -> results}

print(f"开始 Exa 基准测试：{len(KEYWORDS)} 个关键词，每个关键词 {RESULTS_PER_KEYWORD} 条结果")
print("=" * 80)

for i, kw in enumerate(KEYWORDS):
    print(f"\n[{i+1}/{len(KEYWORDS)}] 搜索: {kw}")
    all_data[kw] = {}
    
    # Exa only
    print("  -> Exa (AI语义)...", end=" ", flush=True)
    exa_res = search_exa(kw)
    all_data[kw]['exa'] = exa_res
    print(f"{len(exa_res)} 个结果")
    
    time.sleep(1)

# ── Analyze ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("Exa 分析结果")
print("=" * 80)

engines = ['exa']
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
output_dir = os.path.dirname(os.path.abspath(__file__))
raw_file = os.path.join(output_dir, 'benchmark_raw_v2.json')
with open(raw_file, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)
print(f"\n原始数据已保存到: {raw_file}")

# ── Generate Report ───────────────────────────────────────────────────────────
report = []
report.append(f"# Exa AI 搜索引擎评测报告")
report.append(f"")
report.append(f"- **日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
report.append(f"- **测试关键词**: {len(KEYWORDS)}")
report.append(f"- **每个关键词结果数**: {RESULTS_PER_KEYWORD} 条")
report.append(f"- **搜索引擎**: Exa (AI语义搜索)")
report.append(f"")
report.append(f"---")
report.append(f"")

# Summary
report.append(f"## 摘要")
report.append(f"")
report.append(f"| 指标 | Exa |")
report.append(f"|---|---|")
report.append(f"| 总结果数 | {stats['exa']['total']} |")
report.append(f"| 唯一域名数 | {len(stats['exa']['unique_domains'])} |")
report.append(f"| AI相关命中数 | {stats['exa']['ai_relevant']} |")
report.append(f"| 潜在竞争对手域名数 | {len(stats['exa']['competitor_domains'])} |")
report.append(f"")
report.append(f"---")
report.append(f"")

# Per-keyword breakdown
report.append(f"## 按关键词细分")
report.append(f"")
report.append(f"| 关键词 | 总数 | 唯一域名 | AI相关 | 竞争对手域名 |")
report.append(f"|---|---|---|---|---|")
for kw, kw_stats in keyword_details.items():
    e = kw_stats['exa']
    report.append(f"| {kw} | {e['count']} | {e['domains']} | {e['ai_count']} | {len(e['comp_domains'])} |")
report.append(f"")

# Sample results table
report.append(f"## 样本搜索结果（每个关键词前3名）")
report.append(f"")
for kw, kw_stats in keyword_details.items():
    report.append(f"### `{kw}`")
    report.append(f"")
    report.append(f"| # | 域名 | 标题 | AI? |")
    report.append(f"|---|---|---|---|")
    results = kw_stats['exa'].get('results', [])[:3]
    for j, r in enumerate(results):
        d = extract_domain(r['link'])
        is_ai = 'Y' if is_potential_competitor(r) else ''
        title = r['title'][:50]
        report.append(f"| {j+1} | {d} | {title} | {is_ai} |")
    report.append(f"")

# Exa unique domains
report.append(f"## Exa 发现的竞争对手域名")
report.append(f"")
all_comp_domains = sorted(stats['exa']['competitor_domains'])
report.append(f"共发现 **{len(all_comp_domains)}** 个潜在竞争对手域名：")
report.append(f"")
for i in range(0, len(all_comp_domains), 5):
    batch = all_comp_domains[i:i+5]
    report.append(f"- {', '.join(batch)}")
report.append(f"")

report_text = "\n".join(report)

report_file = os.path.join(output_dir, 'exa_benchmark_report.md')
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report_text)

print(f"\n报告已保存到: {report_file}")
print(f"发现的唯一 AI 竞争对手域名总数: {len(stats['exa']['competitor_domains'])}")
print(f"\n=== Exa 基准测试完成 ===")
