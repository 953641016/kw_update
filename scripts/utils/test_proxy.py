import requests

session = requests.Session()
session.trust_env = False
session.proxies = {
    'http': 'socks5h://0npa6:NYt6R@23.137.220.250:1000',
    'https': 'socks5h://0npa6:NYt6R@23.137.220.250:1000'
}

print("Testing proxy with httpbin...")
try:
    r = session.get('https://httpbin.org/ip', timeout=10)
    print(f'Proxy works! Response: {r.text.strip()}')
except Exception as e:
    print(f'Proxy failed: {type(e).__name__}: {e}')

print("\nTesting Perplexity API via proxy...")
import os
from dotenv import load_dotenv
load_dotenv('/Users/zhangjian/project/keyword/scripts/.env')
PPLX_KEY = os.getenv("PERPLEXITY_API_KEY")

try:
    r = session.post(
        'https://api.perplexity.ai/chat/completions',
        headers={'Authorization': f'Bearer {PPLX_KEY}', 'Content-Type': 'application/json'},
        json={"model": "sonar", "messages": [{"role": "user", "content": "Reply: OK"}], "temperature": 0},
        timeout=20
    )
    print(f'Perplexity OK! HTTP {r.status_code}: {r.text[:200]}')
except Exception as e:
    print(f'Perplexity failed: {type(e).__name__}: {e}')
