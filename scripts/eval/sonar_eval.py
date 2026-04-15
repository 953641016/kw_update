#!/usr/bin/env python3
"""
sonar_eval.py - 通过 SOCKS5 代理评测 Sonar/Sonar Pro 的发布日期识别能力
"""
import json, os, re, time
import requests

from dotenv import load_dotenv
load_dotenv('/Users/zhangjian/project/keyword/scripts/.env')

PPLX_KEY = os.getenv("PERPLEXITY_API_KEY")
PROXY_URL = "socks5h://0npa6:NYt6R@23.137.220.250:1000"

SYSTEM_PROMPT = (
    "You are an AI product release date expert with web search capability. "
    "Find the EXACT date when this product was first RELEASED or made publicly available.\n\n"
    "RULES:\n"
    "1. The FULL product name must match exactly.\n"
    "2. ONLY count actual RELEASE/LAUNCH dates. NOT leaks, rumors, 'coming soon'.\n"
    "3. If the product does NOT exist, output null with reason 'not_exist'.\n"
    "4. If announced but NOT released, output null with reason 'not_released'.\n"
    "5. If released but date unknown, output null with reason 'date_unknown'.\n"
    "6. Do NOT guess.\n\n"
    'Output ONLY valid JSON:\n'
    '{"date": "YYYY-MM-DD", "event": "brief description"}\n'
    'or {"date": null, "reason": "not_exist|not_released|date_unknown"}'
)

def query_sonar(keyword, model, session):
    try:
        resp = session.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                'Authorization': f'Bearer {PPLX_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Product: {keyword}"}
                ],
                "temperature": 0
            },
            timeout=30
        )
        data = resp.json()
        answer = data['choices'][0]['message']['content'].strip()
        citations = data.get('citations', [])

        match = re.search(r'\{[\s\S]*\}', answer)
        result = json.loads(match.group(0)) if match else json.loads(answer)

        return {
            "date": result.get('date'),
            "reason": result.get('reason', ''),
            "event": result.get('event', ''),
            "citations": len(citations),
            "raw_answer": answer[:200]
        }
    except Exception as e:
        print(f"  [ERROR] {model}: {type(e).__name__}: {e}")
        return {"date": None, "reason": "error", "event": str(e)[:100], "citations": 0, "raw_answer": ""}

def main():
    with open('/Users/zhangjian/project/keyword/data/release_date_keywords.json') as f:
        keywords = json.load(f)

    # Setup session with SOCKS5 proxy
    session = requests.Session()
    session.trust_env = False
    session.proxies = {
        'http': PROXY_URL,
        'https': PROXY_URL
    }

    # Quick connectivity test
    print("Testing Perplexity API connectivity via proxy...")
    try:
        test = session.post(
            "https://api.perplexity.ai/chat/completions",
            headers={'Authorization': f'Bearer {PPLX_KEY}', 'Content-Type': 'application/json'},
            json={"model": "sonar", "messages": [{"role": "user", "content": "Reply with just: OK"}], "temperature": 0},
            timeout=15
        )
        print(f"  Connectivity OK (HTTP {test.status_code})")
    except Exception as e:
        print(f"  Connectivity FAILED: {e}")
        print("  Aborting.")
        return

    print(f"\nEvaluating {len(keywords)} keywords with Sonar and Sonar Pro...\n")
    all_results = {}

    for i, kw in enumerate(keywords):
        print(f"[{i+1}/{len(keywords)}] {kw}")
        kw_data = {}
        for model in ["sonar", "sonar-pro"]:
            print(f"  Querying {model}...")
            result = query_sonar(kw, model, session)
            kw_data[model] = result
            d = result['date'] or 'NULL'
            c = result['citations']
            r = result.get('reason', '')
            evt = result.get('event', '')[:40]
            print(f"    -> date={d}, citations={c}, reason={r}, event={evt}")
            time.sleep(1.5)
        all_results[kw] = kw_data
        time.sleep(0.5)

    with open('/Users/zhangjian/project/keyword/data/sonar_eval.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Load previous search API results
    with open('/Users/zhangjian/project/keyword/data/release_date_eval.json') as f:
        prev = json.load(f)

    # Combined summary
    print("\n" + "=" * 115)
    print(f"{'Keyword':<28} | {'Serper':<12} | {'Brave':<12} | {'Tavily':<12} | {'Sonar':<12} | {'Sonar Pro':<12}")
    print("-" * 115)

    scores = {"Serper": 0, "Brave": 0, "Tavily": 0, "sonar": 0, "sonar-pro": 0}
    for kw in keywords:
        s = prev.get(kw, {}).get("Serper", {}).get("extracted_date") or "NULL"
        b = prev.get(kw, {}).get("Brave", {}).get("extracted_date") or "NULL"
        t = prev.get(kw, {}).get("Tavily", {}).get("extracted_date") or "NULL"
        sn = all_results[kw]["sonar"]["date"] or "NULL"
        sp = all_results[kw]["sonar-pro"]["date"] or "NULL"

        for api, val in [("Serper",s),("Brave",b),("Tavily",t),("sonar",sn),("sonar-pro",sp)]:
            if val != "NULL":
                scores[api] += 1

        print(f"{kw:<28} | {s:<12} | {b:<12} | {t:<12} | {sn:<12} | {sp:<12}")

    print("-" * 115)
    print(f"{'Extracted (out of 10)':<28} | {scores['Serper']:<12} | {scores['Brave']:<12} | {scores['Tavily']:<12} | {scores['sonar']:<12} | {scores['sonar-pro']:<12}")

    # Sonar citation stats
    sonar_cites = sum(all_results[kw]["sonar"]["citations"] for kw in keywords)
    pro_cites = sum(all_results[kw]["sonar-pro"]["citations"] for kw in keywords)
    print(f"{'Total citations':<28} | {'--':<12} | {'--':<12} | {'--':<12} | {sonar_cites:<12} | {pro_cites:<12}")

    print(f"\n[OK] Results saved to sonar_eval.json")

if __name__ == "__main__":
    main()
