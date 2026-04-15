"""
extract_tables.py
从 search_snapshots.json + local_google_parsed_v2.json 中提取每个关键词的
简化对比表（位置、标题、域名），输出为 Markdown 格式便于直接嵌入报告。
"""
import json
from urllib.parse import urlparse

def get_domain(url):
    try:
        if not url: return ""
        url = url.split(' ')[0].split(u'\u203a')[0].strip()
        if not url.startswith('http'):
            url = 'https://' + url
        return urlparse(url).netloc.lower().replace("www.", "")
    except:
        return ""

def shorten(title, maxlen=45):
    if not title: return ""
    return title[:maxlen] + "..." if len(title) > maxlen else title

with open("data/search_snapshots.json", "r", encoding="utf-8") as f:
    snapshots = json.load(f)
with open("data/local_google_parsed_v2.json", "r", encoding="utf-8") as f:
    google_gt = json.load(f)

# Also load HappyHorse from api_snapshots.json
with open("data/api_snapshots.json", "r", encoding="utf-8") as f:
    hh_data = json.load(f)

all_keywords = list(google_gt.keys()) + ["HappyHorse-1.0"]

output_lines = []

for kw in all_keywords:
    output_lines.append(f"\n### {kw}\n")
    
    # Get Google results
    if kw == "HappyHorse-1.0":
        g_results = hh_data.get("Local_Google", [])
    else:
        g_results = google_gt.get(kw, [])
    
    # Get API results
    if kw in snapshots:
        s_results = snapshots[kw].get("Serper", [])
        b_results = snapshots[kw].get("Brave", [])
        t_results = snapshots[kw].get("Tavily", [])
    elif kw == "HappyHorse-1.0":
        s_results = hh_data.get("Serper", [])
        b_results = hh_data.get("Brave", [])
        t_results = hh_data.get("Tavily", [])
    else:
        s_results = b_results = t_results = []
    
    # Build comparison table
    output_lines.append("| # | Google (Ground Truth) | Serper | Brave | Tavily |")
    output_lines.append("| :---: | :--- | :--- | :--- | :--- |")
    
    for pos in range(1, 11):
        cells = []
        
        # Google
        if pos <= len(g_results):
            r = g_results[pos-1]
            d = get_domain(r.get("url", ""))
            t = shorten(r.get("title", ""))
            cells.append(f"`{d}`<br>{t}")
        else:
            cells.append("—")
        
        # Serper
        if pos <= len(s_results):
            r = s_results[pos-1]
            d = get_domain(r.get("link") or r.get("url", ""))
            t = shorten(r.get("title", ""))
            cells.append(f"`{d}`<br>{t}")
        else:
            cells.append("—")
        
        # Brave
        if pos <= len(b_results):
            r = b_results[pos-1]
            d = get_domain(r.get("url", ""))
            t = shorten(r.get("title", ""))
            cells.append(f"`{d}`<br>{t}")
        else:
            cells.append("—")
        
        # Tavily
        if pos <= len(t_results):
            r = t_results[pos-1]
            d = get_domain(r.get("url", ""))
            t = shorten(r.get("title", ""))
            cells.append(f"`{d}`<br>{t}")
        else:
            cells.append("—")
        
        output_lines.append(f"| {pos} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")

with open("data/keyword_tables.md", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"[OK] Generated tables for {len(all_keywords)} keywords -> keyword_tables.md")
