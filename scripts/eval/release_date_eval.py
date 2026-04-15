#!/usr/bin/env python3
"""
release_date_eval.py - 评测 Brave/Serper/Tavily/Exa 在"模型发布日期识别"场景下的能力

方法：
1. 对 10 个关键词分别用 4 个 API 搜索 "{keyword} release date"
2. 收集每个 API 返回的片段（snippet）中是否包含日期信息
3. 用 GPT-4o 从片段中提取日期
4. 对比各 API 的日期提取成功率和一致性
"""

import json
import os
import re
import ssl
import time
import urllib.request
import urllib.parse
from datetime import datetime

# Load env
from dotenv import load_dotenv
load_dotenv('/Users/zhangjian/project/keyword/scripts/.env')

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

# Bypass proxy
for var in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
            'all_proxy', 'ALL_PROXY'):
    os.environ.pop(var, None)

DATE_FIND = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
DATE_FIND_FLEX = re.compile(r'\b(\d{4}-\d{2}-\d{2}|\d{4}-\d{2}|\d{4})\b')

def _ssl_ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except:
        return ssl._create_unverified_context()

SSL_CTX = _ssl_ctx()

def http_post(url, headers, payload, timeout=20):
    data = payload.encode('utf-8') if isinstance(payload, str) else payload
    handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(handler, urllib.request.HTTPSHandler(context=SSL_CTX))
    req = urllib.request.Request(url, headers=headers, method='POST', data=data)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.info().get('Content-Encoding') == 'gzip':
                import gzip
                raw = gzip.decompress(raw)
            return json.loads(raw.decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"  [ERROR] {type(e).__name__}: {e}")
        return None

def http_get(url, headers, timeout=15):
    handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(handler, urllib.request.HTTPSHandler(context=SSL_CTX))
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.info().get('Content-Encoding') == 'gzip':
                import gzip
                raw = gzip.decompress(raw)
            return json.loads(raw.decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"  [ERROR] {type(e).__name__}: {e}")
        return None

# ── Search API wrappers ──

def search_serper(query):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": query, "num": 5})
    data = http_post("https://google.serper.dev/search", headers, payload)
    if not data:
        return []
    results = []
    for r in data.get('organic', [])[:5]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("link", ""),
            "snippet": r.get("snippet", ""),
            "date": r.get("date", "")
        })
    return results

def search_brave(query):
    headers = {'Accept': 'application/json', 'Accept-Encoding': 'gzip',
               'X-Subscription-Token': BRAVE_API_KEY}
    url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count=5"
    data = http_get(url, headers)
    if not data:
        return []
    results = []
    for r in data.get('web', {}).get('results', [])[:5]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", ""),
            "date": r.get("page_age", r.get("age", ""))
        })
    return results

def search_tavily(query):
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps({"api_key": TAVILY_API_KEY, "query": query,
                          "search_depth": "basic", "max_results": 5})
    data = http_post("https://api.tavily.com/search", headers, payload)
    if not data:
        return []
    results = []
    for r in data.get('results', [])[:5]:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", "")[:500],
            "date": ""
        })
    return results

def search_exa(query):
    import subprocess
    payload = json.dumps({
        "query": query,
        "numResults": 5,
        "type": "auto",
        "contents": {
            "text": {"maxCharacters": 500},
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
        print(f"  [ERROR] Exa curl: {e}")
        return []
    results = []
    for r in data.get('results', [])[:5]:
        # Exa returns publishedDate in ISO 8601
        pub_date = r.get("publishedDate", "")
        snippet = r.get("text", "")
        if not snippet:
            highlights = r.get("highlights", [])
            snippet = " ".join(highlights) if highlights else ""
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": snippet[:500],
            "date": pub_date
        })
    return results

# ── GPT-4o date extraction ──

EXTRACT_PROMPT = (
    "You are an AI product release date expert. Based on the search results below, "
    "find the EXACT date when this product was first RELEASED or made publicly available.\n\n"
    "RULES:\n"
    "1. The FULL product name must match exactly.\n"
    "2. ONLY count actual RELEASE/LAUNCH dates. NOT: leaks, rumors, 'coming soon'.\n"
    "3. If unsure, output NULL.\n\n"
    "Output ONLY one line: YYYY-MM-DD or NULL"
)

def extract_date_gpt(keyword, snippets_text):
    if not OPENAI_API_KEY or not snippets_text.strip():
        return None
    payload = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": f"Product: {keyword}\n\nSearch Results:\n{snippets_text[:3000]}"}
        ],
        "temperature": 0.0, "max_tokens": 50
    })
    headers = {'Authorization': f'Bearer {OPENAI_API_KEY}',
               'Content-Type': 'application/json'}
    data = http_post(f"{OPENAI_BASE_URL}/chat/completions", headers, payload, timeout=30)
    if data:
        try:
            ans = data['choices'][0]['message']['content'].strip()
            if 'NULL' in ans.upper():
                return None
            m = DATE_FIND.search(ans)
            if m:
                return m.group(0)
            m2 = DATE_FIND_FLEX.search(ans)
            if m2:
                return m2.group(0)
        except:
            pass
    return None

def format_snippets(results):
    parts = []
    for r in results:
        date_info = f" [{r['date']}]" if r.get('date') else ""
        parts.append(f"[{r['title']}]{date_info} ({r['url']})\n{r['snippet']}")
    return "\n\n".join(parts)

def has_date_in_results(results):
    """Check if any result has explicit date metadata"""
    count = 0
    for r in results:
        if r.get('date'):
            count += 1
    return count

# ── Main evaluation ──

def main():
    with open('/Users/zhangjian/project/keyword/data/release_date_keywords.json') as f:
        keywords = json.load(f)

    print(f"Evaluating {len(keywords)} keywords for release date extraction...\n")

    all_results = {}

    for i, kw in enumerate(keywords):
        print(f"[{i+1}/{len(keywords)}] {kw}")

        query = f'"{kw}" release date'
        kw_data = {}

        for api_name, search_fn in [("Serper", search_serper),
                                     ("Brave", search_brave),
                                     ("Tavily", search_tavily),
                                     ("Exa", search_exa)]:
            print(f"  Searching {api_name}...")
            results = search_fn(query)
            snippets = format_snippets(results)
            date_metadata_count = has_date_in_results(results)

            print(f"  Extracting date via GPT-4o...")
            extracted_date = extract_date_gpt(kw, snippets)

            kw_data[api_name] = {
                "result_count": len(results),
                "date_metadata_count": date_metadata_count,
                "extracted_date": extracted_date,
                "top_snippets": [{"title": r["title"][:60], "date": r.get("date", "")} for r in results[:3]]
            }
            print(f"    -> results={len(results)}, date_meta={date_metadata_count}, extracted={extracted_date}")
            time.sleep(0.5)

        all_results[kw] = kw_data
        time.sleep(1)

    # Save raw results
    with open('/Users/zhangjian/project/keyword/data/release_date_eval.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Print summary table
    print("\n" + "=" * 100)
    print(f"{'Keyword':<30} | {'Serper':<12} | {'Brave':<12} | {'Tavily':<12} | {'Exa':<12} | Match")
    print("-" * 100)
    
    scores = {"Serper": 0, "Brave": 0, "Tavily": 0, "Exa": 0}
    date_meta_scores = {"Serper": 0, "Brave": 0, "Tavily": 0, "Exa": 0}

    for kw, data in all_results.items():
        s = data["Serper"]["extracted_date"] or "NULL"
        b = data["Brave"]["extracted_date"] or "NULL"
        t = data["Tavily"]["extracted_date"] or "NULL"
        e = data["Exa"]["extracted_date"] or "NULL"
        
        # Check consensus
        dates = [d for d in [s, b, t, e] if d != "NULL"]
        match = "---"
        if len(dates) >= 2:
            unique_dates = set(dates)
            if len(unique_dates) == 1:
                match = "ALL AGREE"
            else:
                # Find which APIs agree
                pairs = []
                api_vals = {"S": s, "B": b, "T": t, "E": e}
                for n1, v1 in api_vals.items():
                    for n2, v2 in api_vals.items():
                        if n1 < n2 and v1 == v2 and v1 != "NULL":
                            pairs.append(f"{n1}={n2}")
                match = ",".join(pairs) if pairs else "DISAGREE"

        for api in ["Serper", "Brave", "Tavily", "Exa"]:
            if data[api]["extracted_date"]:
                scores[api] += 1
            date_meta_scores[api] += data[api]["date_metadata_count"]
        
        print(f"{kw:<30} | {s:<12} | {b:<12} | {t:<12} | {e:<12} | {match}")

    print("-" * 100)
    print(f"{'Date extracted (out of 10)':<30} | {scores['Serper']:<12} | {scores['Brave']:<12} | {scores['Tavily']:<12} | {scores['Exa']:<12}")
    print(f"{'Date metadata in results':<30} | {date_meta_scores['Serper']:<12} | {date_meta_scores['Brave']:<12} | {date_meta_scores['Tavily']:<12} | {date_meta_scores['Exa']:<12}")

    print(f"\n[OK] Full results saved to release_date_eval.json")

if __name__ == "__main__":
    main()
