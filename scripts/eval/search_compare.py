import requests
import json
import os
from dotenv import load_dotenv

# Try to load .env from root, fallback to scripts/.env
if os.path.exists('./.env'):
    load_dotenv('./.env')
elif os.path.exists('./scripts/.env'):
    load_dotenv('./scripts/.env')

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

QUERY = "HappyHorse-1.0"
TIMEOUT = 15

session = requests.Session()
session.trust_env = False  # Ignore system and env proxies

snapshots = {
    "Query": QUERY,
    "Serper": [],
    "Brave": [],
    "Tavily": [],
    "Errors": {}
}

print("### 1. Serper API")
try:
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    payload = json.dumps({"q": QUERY, "num": 10})
    response = session.post("https://google.serper.dev/search", headers=headers, data=payload, timeout=TIMEOUT)
    if response.status_code == 200:
        results = response.json().get('organic', [])[:10]
        snapshots["Serper"] = results
        for i, res in enumerate(results):
            print(f"{i+1}. [{res.get('title')}]({res.get('link')})")
    else:
        print(f"Error {response.status_code}: {response.text}")
        snapshots["Errors"]["Serper"] = f"Error {response.status_code}: {response.text}"
except Exception as e:
    print(f"Failed to connect to Serper API: {e}")
    snapshots["Errors"]["Serper"] = str(e)

print("\n### 2. Brave Search API")
try:
    headers = {
        'Accept': 'application/json',
        'X-Subscription-Token': BRAVE_API_KEY
    }
    response = session.get(f"https://api.search.brave.com/res/v1/web/search?q={QUERY}&count=10", headers=headers, timeout=TIMEOUT)
    if response.status_code == 200:
        results = response.json().get('web', {}).get('results', [])[:10]
        snapshots["Brave"] = results
        for i, res in enumerate(results):
            print(f"{i+1}. [{res.get('title')}]({res.get('url')})")
    else:
        print(f"Error {response.status_code}: {response.text}")
        snapshots["Errors"]["Brave"] = f"Error {response.status_code}: {response.text}"
except Exception as e:
    print(f"Failed to connect to Brave Search API: {e}")
    snapshots["Errors"]["Brave"] = str(e)

print("\n### 3. Tavily API")
try:
    headers = {
        'Content-Type': 'application/json'
    }
    payload = json.dumps({"api_key": TAVILY_API_KEY, "query": QUERY, "search_depth": "basic", "max_results": 10})
    response = session.post("https://api.tavily.com/search", headers=headers, data=payload, timeout=TIMEOUT)
    if response.status_code == 200:
        results = response.json().get('results', [])[:10]
        snapshots["Tavily"] = results
        for i, res in enumerate(results):
            print(f"{i+1}. [{res.get('title')}]({res.get('url')})")
    else:
         print(f"Error {response.status_code}: {response.text}")
         snapshots["Errors"]["Tavily"] = f"Error {response.status_code}: {response.text}"
except Exception as e:
    print(f"Failed to connect to Tavily API: {e}")
    snapshots["Errors"]["Tavily"] = str(e)

with open("data/api_snapshots.json", "w", encoding="utf-8") as f:
    json.dump(snapshots, f, ensure_ascii=False, indent=4)
print("\n[✔] Snapshots saved to data/api_snapshots.json")
