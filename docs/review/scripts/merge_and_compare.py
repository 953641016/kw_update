"""
Merge Exa data with previous benchmark and generate complete comparison report
合并 Exa 数据与之前的基准测试，生成完整对比报告
"""
import json, os
from urllib.parse import urlparse
from datetime import datetime
from collections import defaultdict

def extract_domain(url):
    try:
        parsed = urlparse(url)
        d = parsed.hostname or ''
        return d.replace('www.', '').lower().strip()
    except:
        return ''

# ── Load data ─────────────────────────────────────────────────────────────────
output_dir = os.path.dirname(os.path.abspath(__file__))

# Load previous benchmark (serper, brave, tavily)
with open(os.path.join(output_dir, 'benchmark_raw.json'), 'r', encoding='utf-8') as f:
    old_data = json.load(f)

# Load Exa benchmark
with open(os.path.join(output_dir, 'benchmark_raw_v2.json'), 'r', encoding='utf-8') as f:
    exa_data = json.load(f)

# Merge: add exa to each keyword
all_data = {}
keywords = list(old_data.keys())

for kw in keywords:
    all_data[kw] = {
        'serper': old_data[kw].get('serper', []),
        'brave': old_data[kw].get('brave', []),
        'tavily': old_data[kw].get('tavily', []),
        'exa': exa_data[kw].get('exa', [])
    }

print(f"已合并 {len(keywords)} 个关键词的数据")
print(f"引擎: Serper, Brave, Tavily, Exa")

# ── Noise domains ─────────────────────────────────────────────────────────────
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

# ── Analyze ───────────────────────────────────────────────────────────────────
print("\n开始分析...")

engines = ['serper', 'brave', 'tavily', 'exa']
stats = {e: {'total': 0, 'unique_domains': set(), 'ai_relevant': 0, 'competitor_domains': set()} for e in engines}

keyword_details = {}

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
            'results': results[:5]
        }
    keyword_details[kw] = kw_stats

print("分析完成")

# ── Generate Report ───────────────────────────────────────────────────────────
print("\n生成报告...")

report = []
report.append(f"# 搜索引擎基准测试报告")
report.append(f"")
report.append(f"- **日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
report.append(f"- **测试关键词**: {len(keywords)}")
report.append(f"- **每个关键词结果数**: 50 条")
report.append(f"- **对比引擎**: Serper (Google), Brave, Tavily, Exa (AI语义搜索)")
report.append(f"")
report.append(f"---")
report.append(f"")

# Summary
report.append(f"## 摘要")
report.append(f"")
report.append(f"| 指标 | Serper | Brave | Tavily | Exa |")
report.append(f"|---|---|---|---|---|")
report.append(f"| 总结果数 | {stats['serper']['total']} | {stats['brave']['total']} | {stats['tavily']['total']} | {stats['exa']['total']} |")
report.append(f"| 唯一域名数 | {len(stats['serper']['unique_domains'])} | {len(stats['brave']['unique_domains'])} | {len(stats['tavily']['unique_domains'])} | {len(stats['exa']['unique_domains'])} |")
report.append(f"| AI相关命中数 | {stats['serper']['ai_relevant']} | {stats['brave']['ai_relevant']} | {stats['tavily']['ai_relevant']} | {stats['exa']['ai_relevant']} |")
report.append(f"| 潜在竞争对手域名数 | {len(stats['serper']['competitor_domains'])} | {len(stats['brave']['competitor_domains'])} | {len(stats['tavily']['competitor_domains'])} | {len(stats['exa']['competitor_domains'])} |")
report.append(f"")

# Auto-determine winner
ai_scores = {e: stats[e]['ai_relevant'] for e in engines}
domain_scores = {e: len(stats[e]['competitor_domains']) for e in engines}
best_ai = max(ai_scores, key=ai_scores.get)
best_domain = max(domain_scores, key=domain_scores.get)

engine_names = {'serper': 'Serper (Google)', 'brave': 'Brave', 'tavily': 'Tavily', 'exa': 'Exa'}
report.append(f"**AI相关结果获胜者**: **{engine_names[best_ai].upper()}** ({ai_scores[best_ai]} 个命中)")
report.append(f"")
report.append(f"**唯一竞争对手域名获胜者**: **{engine_names[best_domain].upper()}** ({domain_scores[best_domain]} 个域名)")
report.append(f"")
report.append(f"---")
report.append(f"")

# Per-keyword breakdown
report.append(f"## 按关键词细分")
report.append(f"")
report.append(f"| 关键词 | Serper (总数/AI) | Brave (总数/AI) | Tavily (总数/AI) | Exa (总数/AI) |")
report.append(f"|---|---|---|---|---|")
for kw, kw_stats in keyword_details.items():
    s = kw_stats['serper']
    b = kw_stats['brave']
    t = kw_stats['tavily']
    e = kw_stats['exa']
    report.append(f"| {kw} | {s['count']}/{s['ai_count']} | {b['count']}/{b['ai_count']} | {t['count']}/{t['ai_count']} | {e['count']}/{e['ai_count']} |")
report.append(f"")

# Overlap analysis
report.append(f"## 域名重叠分析")
report.append(f"")
s_dom = stats['serper']['competitor_domains']
b_dom = stats['brave']['competitor_domains']
t_dom = stats['tavily']['competitor_domains']
e_dom = stats['exa']['competitor_domains']

# 计算各种组合
all_comp = s_dom | b_dom | t_dom | e_dom
only_serper = s_dom - b_dom - t_dom - e_dom
only_brave = b_dom - s_dom - t_dom - e_dom
only_tavily = t_dom - s_dom - b_dom - e_dom
only_exa = e_dom - s_dom - b_dom - t_dom
shared_all = s_dom & b_dom & t_dom & e_dom

report.append(f"| 类别 | 数量 | 域名示例 |")
report.append(f"|---|---|---|")
report.append(f"| 所有4个引擎 | {len(shared_all)} | {', '.join(sorted(shared_all)[:10])} |")
report.append(f"| 仅 Serper | {len(only_serper)} | {', '.join(sorted(only_serper)[:10])} |")
report.append(f"| 仅 Brave | {len(only_brave)} | {', '.join(sorted(only_brave)[:10])} |")
report.append(f"| 仅 Tavily | {len(only_tavily)} | {', '.join(sorted(only_tavily)[:10])} |")
report.append(f"| 仅 Exa | {len(only_exa)} | {', '.join(sorted(only_exa)[:10])} |")
report.append(f"| 总计唯一 | {len(all_comp)} | - |")
report.append(f"")

# Sample results table
report.append(f"## 样本搜索结果（每个引擎每个关键词前3名）")
report.append(f"")
for kw, kw_stats in keyword_details.items():
    report.append(f"### `{kw}`")
    report.append(f"")
    report.append(f"| 引擎 | # | 域名 | 标题 | AI? |")
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

# Save report
report_file = os.path.join(output_dir, 'search_benchmark_report_final.md')
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report_text)

print(f"\n✅ 报告已保存到: {report_file}")
print(f"\n=== 汇总统计 ===")
print(f"总唯一竞争对手域名: {len(all_comp)}")
print(f"  - Serper 独有: {len(only_serper)}")
print(f"  - Brave 独有: {len(only_brave)}")
print(f"  - Tavily 独有: {len(only_tavily)}")
print(f"  - Exa 独有: {len(only_exa)}")
print(f"  - 4个引擎共有: {len(shared_all)}")
print(f"\n=== 基准测试完成 ===")
