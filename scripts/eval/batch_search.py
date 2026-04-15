import requests
import json
import os
import time
from dotenv import load_dotenv

# Load env variables
if os.path.exists('./.env'):
    load_dotenv('./.env')
elif os.path.exists('./scripts/.env'):
    load_dotenv('./scripts/.env')

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

TIMEOUT = 15
session = requests.Session()
session.trust_env = False  # Critical: Bypass system proxies

def fetch_serper(query):
    try:
        headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
        payload = json.dumps({"q": query, "num": 10})
        response = session.post("https://google.serper.dev/search", headers=headers, data=payload, timeout=TIMEOUT)
        return response.json().get('organic', [])[:10] if response.status_code == 200 else []
    except: return []

def fetch_brave(query):
    try:
        headers = {'Accept': 'application/json', 'X-Subscription-Token': BRAVE_API_KEY}
        response = session.get(f"https://api.search.brave.com/res/v1/web/search?q={query}&count=10", headers=headers, timeout=TIMEOUT)
        return response.json().get('web', {}).get('results', [])[:10] if response.status_code == 200 else []
    except: return []

def fetch_tavily(query):
    try:
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({"api_key": TAVILY_API_KEY, "query": query, "search_depth": "basic", "max_results": 10})
        response = session.post("https://api.tavily.com/search", headers=headers, data=payload, timeout=TIMEOUT)
        return response.json().get('results', [])[:10] if response.status_code == 200 else []
    except: return []

def main():
    # 1. Load ground truth
    with open("data/local_google_parsed.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
    
    # 2. Keywords to process
    keywords = list(ground_truth.keys())
    if "HappyHorse-1.0" not in keywords:
        keywords.append("HappyHorse-1.0")

    # 3. Load existing HappyHorse data if available to avoid re-searching it (optional)
    # For consistency, we search all
    
    all_snapshots = {}

    for kw in keywords:
        print(f"Processing: {kw}...")
        results = {
            "Local_Google": ground_truth.get(kw, []),
            "Serper": fetch_serper(kw),
            "Brave": fetch_brave(kw),
            "Tavily": fetch_tavily(kw)
        }
        
        # If HappyHorse-1.0 results are missing from local_google_parsed (which they are), 
        # we try to get them from api_snapshots.json
        if kw == "HappyHorse-1.0" and not results["Local_Google"]:
            try:
                with open("data/api_snapshots.json", "r") as f:
                    old_data = json.load(f)
                    results["Local_Google"] = old_data.get("Local_Google", [])
            except: pass

        all_snapshots[kw] = results
        time.sleep(1) # Polite delay

    # 4. Save final snapshot
    with open("data/search_snapshots.json", "w", encoding="utf-8") as f:
        json.dump(all_snapshots, f, ensure_ascii=False, indent=4)
    
    print(f"\n[✔] Successfully merged {len(keywords)} keywords into search_snapshots.json")

if __name__ == "__main__":
    main()
