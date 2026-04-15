"""
parse_google_v2.py
修复版：根据 google.md 中的 "------" / "----" 分隔线 + "N、KeywordName" 标题行
来精确分割关键词段落，避免将结果内部的数字编号误判为关键词边界。
"""
import json
import re

KNOWN_KEYWORDS = [
    "ElevenMusic", "Ideogram Layerize", "PixVerse C1", "Mureka V9",
    "DreamID-Omni", "FireRed Image Edit", "SkyReels V4", "wan 2.7", "Netflix VOID"
]

def parse_google_md(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by horizontal rules (--- or ------) which separate keywords
    # First, find keyword section boundaries using the "N、KeywordName" pattern
    # But only match lines that start with a digit followed by 、 and one of the known keywords
    sections = {}
    
    # Build a regex that matches keyword headers like "1、ElevenMusic" or "3、PixVerse C1"
    # The line typically appears after a "------" divider
    keyword_pattern = re.compile(
        r'^(\d+)[、．.]\s*(' + '|'.join(re.escape(k) for k in KNOWN_KEYWORDS) + r')',
        re.MULTILINE
    )
    
    matches = list(keyword_pattern.finditer(content))
    
    for i, match in enumerate(matches):
        kw_name = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        
        # Also trim any leading "------" from next section
        section_text = content[start:end]
        # Remove trailing dividers
        section_text = re.sub(r'-{3,}\s*$', '', section_text)
        
        sections[kw_name] = section_text.strip()
    
    results = {}
    
    for kw_name, section_text in sections.items():
        lines = section_text.split('\n')
        lines = [line.strip() for line in lines]
        
        # Filter out noise lines
        skip_patterns = [
            '赞助商搜索结果', '隐藏赞助商搜索结果', '焦点新闻', '相关问题',
            '短视频', '查看全部', '更多新闻', '更多短视频', '翻译此页',
            '过去一个月内', '缺少字词', '必须包含',
            '站内的其它相关信息', '在此视频中',
        ]
        
        keyword_results = []
        rank = 1
        i = 0
        
        while i < len(lines) and rank <= 10:
            line = lines[i]
            
            # Skip empty and noise lines
            if not line or line == '·' or line.startswith('---'):
                i += 1
                continue
            
            # Skip lines matching skip patterns
            if any(p in line for p in skip_patterns):
                i += 1
                continue
            
            # Skip video/YouTube blocks (duration markers like "6:16", "0:32")
            if re.match(r'^\d+:\d+$', line):
                i += 1
                continue
            
            # Skip "N天前", "N小时前" standalone date lines
            if re.match(r'^\d+[天小]', line):
                i += 1
                continue
                
            # Skip lines that are just counts like "30+ 条评论", "14 个帖子"
            if re.match(r'^\d+[\+]?\s*(条评论|个帖子|次观看|个赞)', line):
                i += 1
                continue
            
            # Skip date patterns like "2026年4月7日"
            if re.match(r'^\d{4}年', line):
                i += 1
                continue
                
            # Skip price patterns like "US$0.09"
            if line.startswith('US$') or re.match(r'^[\d.]+\(\d', line):
                i += 1
                continue
            
            # Skip lines starting with ‎ (invisible char for sub-links)
            if line.startswith('‎') or line.startswith('‎'):
                i += 1
                continue
            
            # Detect URL lines
            if line.startswith('http'):
                url = line
                # Look backward for title (the previous non-empty, non-noise line)
                title = ""
                for j in range(i - 1, max(i - 5, -1), -1):
                    candidate = lines[j].strip()
                    if candidate and candidate != '·' and not candidate.startswith('---'):
                        if not any(p in candidate for p in skip_patterns):
                            title = candidate
                            break
                
                # Look forward for snippet
                snippet = ""
                for j in range(i + 1, min(i + 4, len(lines))):
                    candidate = lines[j].strip()
                    if candidate and candidate != '·' and not candidate.startswith('http'):
                        if not any(p in candidate for p in skip_patterns):
                            if not re.match(r'^\d+:\d+$', candidate):
                                snippet = candidate
                                break
                
                keyword_results.append({
                    "rank": rank,
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
                rank += 1
                i += 1
            else:
                i += 1
        
        results[kw_name] = keyword_results
    
    return results

if __name__ == "__main__":
    ground_truth = parse_google_md("/Users/zhangjian/project/keyword/docs/searchreview/google.md")
    
    # Print summary
    for kw, items in ground_truth.items():
        print(f"\n=== {kw} ({len(items)} results) ===")
        for item in items[:3]:
            print(f"  #{item['rank']}: {item['title']} → {item['url']}")
    
    with open("/Users/zhangjian/project/keyword/data/local_google_parsed_v2.json", "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=4)
    print(f"\n[✔] Saved to local_google_parsed_v2.json")
