import json
import re

def parse_google_md(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by keywords: "N、Keyword"
    sections = re.split(r'\d+[、]\s*', content)
    
    # The first split will be empty or introductory text
    sections = [s.strip() for s in sections if s.strip()]
    
    results = {}
    
    # Standard keywords from google.md in order
    keyword_names = [
        "ElevenMusic", "Ideogram Layerize", "PixVerse C1", "Mureka V9",
        "DreamID-Omni", "FireRed Image Edit", "SkyReels V4", "wan 2.7", "Netflix VOID"
    ]
    
    for i, section in enumerate(sections):
        if i >= len(keyword_names):
            break
            
        keyword = keyword_names[i]
        lines = section.split('\n')
        
        # Clean up lines
        lines = [line.strip() for line in lines if line.strip() and line.strip() != "·" and line.strip() != "翻译此页"]
        
        # Skip "赞助商搜索结果" or "隐藏赞助商搜索结果"
        clean_lines = []
        for line in lines:
            if "赞助商搜索结果" in line or "隐藏赞助商搜索结果" in line or "焦点新闻" in line or "相关问题" in line or "短视频" in line or "视频" in line:
                continue
            clean_lines.append(line)
            
        # Very simple heuristic to find URLs and titles
        # Usually: Title, then URL, then Snippet
        keyword_results = []
        rank = 1
        j = 1 # Skip first line which is keyword name if it's there
        
        while j < len(clean_lines) and rank <= 10:
            line = clean_lines[j]
            # Match URLs
            if line.startswith('http'):
                url = line
                title = clean_lines[j-1] if j > 0 else "No Title"
                snippet = clean_lines[j+1] if j+1 < len(clean_lines) else ""
                
                # If title looks like a sub-item, skip
                if title.strip() == "------" or title.strip() == "---":
                   j += 1
                   continue

                keyword_results.append({
                    "rank": rank,
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
                rank += 1
                j += 2 # Move past title and URL
            else:
                j += 1
                
        results[keyword] = keyword_results
        
    return results

if __name__ == "__main__":
    ground_truth = parse_google_md("/Users/zhangjian/project/keyword/docs/searchreview/google.md")
    with open("/Users/zhangjian/project/keyword/data/local_google_parsed.json", "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=4)
    print("Parsed 9 keywords into local_google_parsed.json")
