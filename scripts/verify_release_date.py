#!/usr/bin/env python3
"""
verify_release_date.py - AI 产品发布日期验证

瀑布流架构：
  ① GitHub Release (免费、精确、适合开源项目)
  ② Sonar Pro (Perplexity 联网 LLM，一步搜索+推理)
  ③ Perplexity Search + GPT-4o 交叉验证 (终极兜底)
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
import ssl
import re
import time
import random
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── 确保不走任何代理 ──────────────────────────────────────────────────
for var in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
            'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY'):
    os.environ.pop(var, None)

DATE_STRICT = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATE_FIND = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
DATE_PARTIAL_YM = re.compile(r'^\d{4}-\d{2}$')
DATE_PARTIAL_Y  = re.compile(r'^\d{4}$')
DATE_FIND_FLEX  = re.compile(r'\b(\d{4}-\d{2}-\d{2}|\d{4}-\d{2}|\d{4})\b')

def log(msg):
    print(f"[debug] {msg}", file=sys.stderr)

def out(d: dict):
    print(json.dumps(d, ensure_ascii=False))

# ─── SSL 上下文 ───────────────────────────────────────────────────────
def _build_ssl_context(verify=True):
    if not verify:
        return ssl._create_unverified_context()
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        try:
            return ssl.create_default_context()
        except Exception:
            return ssl._create_unverified_context()

_SSL_VERIFIED = _build_ssl_context(verify=True)
_SSL_UNVERIFIED = _build_ssl_context(verify=False)

# ─── 核心通信层 ────────────────────────────────────────────────────────
def http_request(url: str, headers: dict = None, timeout: int = 15,
                 method='GET', data=None) -> str:
    merged = {'User-Agent': 'Mozilla/5.0 (compatible; openclaw-verify/1.0)'}
    if headers:
        merged.update(headers)
    if isinstance(data, str):
        data = data.encode('utf-8')

    for attempt, ctx in enumerate([_SSL_VERIFIED, _SSL_UNVERIFIED]):
        no_proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(no_proxy_handler,
                                            urllib.request.HTTPSHandler(context=ctx))
        req = urllib.request.Request(url, headers=merged, method=method, data=data)
        try:
            if attempt == 0:
                log(f"Requesting: {method} {url[:80]}...")
            else:
                log(f"Retry (unverified SSL): {method} {url[:80]}...")
            with opener.open(req, timeout=timeout) as resp:
                import gzip as gz
                raw = resp.read()
                if resp.info().get('Content-Encoding') == 'gzip':
                    raw = gz.decompress(raw)
                return raw.decode('utf-8', errors='replace')
        except ssl.SSLError as e:
            log(f"SSL Error (attempt {attempt+1}): {e}")
            if attempt == 0:
                continue
            return ''
        except Exception as e:
            log(f"Request Error: {type(e).__name__}: {e}")
            if attempt == 0 and 'SSL' in str(e):
                continue
            return ''
    return ''

# ─── 日期格式校验 ──────────────────────────────────────────────────────
def validate_date(s: str) -> str | None:
    if not s or not DATE_STRICT.match(s):
        return None
    try:
        datetime.strptime(s, '%Y-%m-%d')
        return s
    except ValueError:
        return None

def validate_date_flexible(s: str) -> str | None:
    if not s:
        return None
    s = s.strip()
    if DATE_STRICT.match(s):
        try:
            datetime.strptime(s, '%Y-%m-%d')
            return s
        except ValueError:
            return None
    if DATE_PARTIAL_YM.match(s):
        try:
            datetime.strptime(s, '%Y-%m')
            return s
        except ValueError:
            return None
    if DATE_PARTIAL_Y.match(s):
        y = int(s)
        if 1990 <= y <= 2030:
            return s
    return None

# ─── URL 特殊解析 ──────────────────────────────────────────────────────
def check_url_source(url_or_kw):
    u = url_or_kw.lower()
    if 'arxiv.org' in u:
        return {'source': 'arXiv'}
    if 'huggingface.co' in u:
        return {'source': 'HuggingFace'}
    if 'x.com' in u or 'twitter.com' in u:
        m = re.search(r'status/(\d+)', u)
        if m:
            tweet_id = int(m.group(1))
            ts_ms = (tweet_id >> 22) + 1288834974657
            date = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
            return {'date': date, 'source': 'X_Snowflake'}
    return None

# ═══ 第 ① 步：GitHub Release ═════════════════════════════════════════
def check_github(keyword):
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        log("GITHUB_TOKEN not set, skipping GitHub check.")
        return None

    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {token}',
    }

    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(keyword)}&per_page=1&sort=stars"
    body = http_request(url, headers=headers)
    if body:
        try:
            data = json.loads(body)
            items = data.get('items', [])
            if items:
                repo = items[0]
                repo_name = repo['name'].lower()
                stars = repo.get('stargazers_count', 0)
                size_kb = repo.get('size', 0)
                kw_lower = keyword.lower().replace(' ', '-')
                name_match = (kw_lower == repo_name or
                              re.search(r'(?:^|[-_./])' + re.escape(kw_lower) + r'(?:$|[-_./])', repo_name))
                if name_match:
                    if stars < 20 and size_kb < 50:
                        log(f"GitHub skip junk repo: {repo['full_name']} (stars={stars}, size={size_kb}KB)")
                        return None
                    # 优先获取最早的 Release 日期
                    rel_url = f"https://api.github.com/repos/{repo['full_name']}/releases?per_page=100"
                    rel_body = http_request(rel_url, headers=headers, timeout=8)
                    if rel_body:
                        try:
                            releases = json.loads(rel_body)
                            if releases and isinstance(releases, list):
                                oldest = releases[-1]
                                rel_date = oldest.get('published_at', '')[:10]
                                v = validate_date(rel_date)
                                if v:
                                    log(f"GitHub using first Release date: {v}")
                                    return v
                        except Exception:
                            pass
                    return validate_date(repo.get('created_at', '')[:10])
        except Exception:
            pass
    return None

# ═══ 第 ② 步：Sonar Pro (Perplexity 联网 LLM) ════════════════════════
_SONAR_SYSTEM_PROMPT = (
    "You are an AI product release date expert with web search capability. "
    "Find the EXACT date when this product was first RELEASED or made publicly available "
    "(as a beta, preview, or official release that users can actually access or download).\n\n"
    "CRITICAL RULES:\n"
    "1. The FULL product name must match exactly. 'Claude 4.5' ≠ 'Claude 4.6'.\n"
    "2. ONLY count dates when the product was actually RELEASED/LAUNCHED/AVAILABLE. "
    "Do NOT count: CEO mentions, leaks, rumors, 'coming soon' announcements, "
    "roadmap previews, or speculation — these are NOT release dates.\n"
    "3. If the product does NOT exist, output null with reason 'not_exist'.\n"
    "4. If the product is only announced/leaked but NOT yet released, output null with reason 'not_released'.\n"
    "5. If the product exists and is released but you cannot find the exact date, output null with reason 'date_unknown'.\n"
    "6. Do NOT guess or infer dates from related/predecessor products.\n\n"
    "Output ONLY valid JSON (no markdown, no explanation):\n"
    '{"date": "YYYY-MM-DD", "event": "brief description"}\n'
    'or {"date": null, "reason": "not_exist"}\n'
    'or {"date": null, "reason": "not_released"}\n'
    'or {"date": null, "reason": "date_unknown"}'
)

def check_sonar(keyword):
    """返回 (date, should_fallback)"""
    pplx_key = os.environ.get('PERPLEXITY_API_KEY')
    if not pplx_key:
        log("PERPLEXITY_API_KEY not set, skipping Sonar.")
        return None, True

    payload = json.dumps({
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": _SONAR_SYSTEM_PROMPT},
            {"role": "user", "content": f"Product: {keyword}"}
        ],
        "temperature": 0
    })
    res_body = http_request("https://api.perplexity.ai/chat/completions",
                            headers={'Authorization': f'Bearer {pplx_key}',
                                     'Content-Type': 'application/json'},
                            method="POST", data=payload, timeout=30)
    if res_body:
        try:
            data = json.loads(res_body)
            answer = data['choices'][0]['message']['content'].strip()
            citations = data.get('citations', [])
            log(f"Sonar answer: {answer}")
            log(f"Sonar citations: {len(citations)} sources")

            # 解析 JSON 回复
            match = re.search(r'\{[\s\S]*\}', answer)
            if match:
                clean = match.group(0)
            else:
                clean = answer.strip()
            
            result = json.loads(clean)
            date_str = result.get('date')

            if not date_str:
                reason = result.get('reason', 'unknown')
                if reason == 'not_exist':
                    log(f"Sonar: product does NOT exist → NULL, skip fallback")
                    return None, False
                elif reason == 'not_released':
                    log(f"Sonar: product announced/leaked but NOT released → NULL, skip fallback")
                    return None, False
                else:
                    log(f"Sonar: date unknown (reason={reason}) → NULL, will try fallback")
                    return None, True

            # 有日期 + 有引用才采信
            if not citations:
                log("Sonar returned date but NO citations → not trusted")
                return None, True

            v = validate_date(date_str)
            if v:
                return v, False
            v2 = validate_date_flexible(date_str)
            return v2, (v2 is None)  # 如果解析失败则触发兜底
        except Exception as e:
            log(f"Sonar parse error: {e}")
    return None, True

# ═══ 第 ③ 步：Perplexity Search + GPT-4o 交叉验证（兜底）════════════
_EXTRACT_SYSTEM_PROMPT = (
    "You are an expert AI product historian. Your task is to find the VERY FIRST date when a specific "
    "AI product/model became publicly known.\n\n"
    "CRITICAL RULES:\n"
    "1. Find the EARLIEST date when THIS EXACT product first appeared publicly — whether as a beta, "
    "preview, official release, announcement, leak, or paper. Whichever happened FIRST is the answer.\n"
    "2. If the product name includes a version (e.g. 'DeepSeek-V3'), find the date for THAT specific version, "
    "NOT any earlier or later version.\n"
    "3. If the product name has NO version (e.g. 'Claude'), find the date for the VERY FIRST version.\n"
    "4. VERSION DISAMBIGUATION: The FULL product name must match. For example, 'Claude 4.5' is a "
    "DIFFERENT product from 'Claude 4.6'. Do NOT confuse version dates. "
    "If no search result mentions the EXACT full name, output NULL.\n"
    "5. PRODUCT EXISTENCE CHECK: If the search results do NOT contain clear, direct evidence that this "
    "EXACT product exists, you MUST output NULL. Do NOT infer a date from a predecessor.\n"
    "6. Do NOT hallucinate or guess. If unsure, output NULL.\n\n"
    "OUTPUT FORMAT: First write one line of reasoning, then on a new line write ONLY the date:\n"
    "- YYYY-MM-DD if exact day is known\n"
    "- YYYY-MM if only month is known\n"
    "- YYYY if only year is known\n"
    "- NULL if no reliable date exists or the product does not exist\n\n"
    "Example 1:\nChatGPT was first released as a public preview on November 30, 2022.\n2022-11-30\n\n"
    "Example 2:\nNo search result confirms that 'DALL-E 4' exists as a released product.\nNULL"
)

def _parse_extract_response(ans):
    if not ans:
        return None
    m = DATE_FIND.search(ans)
    if m:
        return validate_date(m.group(0))
    m2 = DATE_FIND_FLEX.search(ans)
    return validate_date_flexible(m2.group(0)) if m2 else None

def _call_gpt_extract(keyword, snippets):
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    payload = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Product: {keyword}\n\nSearch Results:\n{snippets[:3000]}"}
        ],
        "temperature": 0.0, "max_tokens": 100
    })
    res_body = http_request(f"{base_url}/chat/completions",
                            headers={'Authorization': f'Bearer {api_key}',
                                     'Content-Type': 'application/json'},
                            method="POST", data=payload)
    if res_body:
        try:
            ans = json.loads(res_body)['choices'][0]['message']['content'].strip()
            return _parse_extract_response(ans)
        except Exception:
            pass
    return None

def _brave_search(query):
    """Brave Search API 获取高质量片段"""
    brave_key = os.environ.get('BRAVE_API_KEY')
    if not brave_key:
        return ""
    url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count=5"
    body = http_request(url,
                        headers={'Accept': 'application/json', 'Accept-Encoding': 'gzip', 'X-Subscription-Token': brave_key})
    if body:
        try:
            data = json.loads(body)
            results = data.get('web', {}).get('results', [])
            parts = []
            for r in results:
                title = r.get('title', '')
                snippet = r.get('description', '')
                url = r.get('url', '')
                parts.append(f"[{title}] ({url}) {snippet}")
            return "\n".join(parts)
        except Exception:
            pass
    return ""

def check_search_gpt_fallback(keyword):
    """Brave Search + GPT-4o 双搜索交叉验证"""
    log("Fallback: Brave Search + GPT-4o cross-validation")

    q1 = f'"{keyword}" release date'
    q2 = f'"{keyword}" official launch announcement'

    date1, date2 = None, None

    for idx, q in enumerate([q1, q2], 1):
        snippets = _brave_search(q)
        if snippets:
            d = _call_gpt_extract(keyword, snippets)
            if idx == 1:
                date1 = d
            else:
                date2 = d

    # 交叉验证
    if date1 and date2:
        try:
            def _parse_flex(ds):
                if DATE_STRICT.match(ds): return datetime.strptime(ds, '%Y-%m-%d')
                if DATE_PARTIAL_YM.match(ds): return datetime.strptime(ds+'-01', '%Y-%m-%d')
                if DATE_PARTIAL_Y.match(ds): return datetime.strptime(ds+'-01-01', '%Y-%m-%d')
                return None

            d1 = _parse_flex(date1)
            d2 = _parse_flex(date2)
            prec1 = len(date1)
            prec2 = len(date2)
            if d1 and d2:
                diff = abs((d1 - d2).days)
                if diff <= 30:
                    result = date1 if d1 <= d2 else date2
                    log(f"Cross-validated: {date1} vs {date2} (diff={diff}d) → {result}")
                    return result
                elif diff > 180 and max(prec1, prec2) < 10:
                    log(f"Cross-validation REJECTED: {date1} vs {date2} (diff={diff}d, low precision) → NULL")
                    return None
                else:
                    if prec1 != prec2:
                        result = date1 if prec1 > prec2 else date2
                    else:
                        result = date1 if d1 <= d2 else date2
                    log(f"Cross-validation diverged: {date1} vs {date2} (diff={diff}d) → {result}")
                    return result
        except Exception:
            pass
        return date1
    elif date1:
        if len(date1) <= 4:
            log(f"Single result too vague: {date1} → NULL")
            return None
        return date1
    elif date2:
        if len(date2) <= 4:
            log(f"Single result too vague: {date2} → NULL")
            return None
        return date2
    return None

# ═══ 主流程 ═══════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keyword', required=True)
    args = parser.parse_args()

    log(f"Starting Waterfall: {args.keyword}")

    # 生产环境 Jitter
    if os.environ.get("PRODUCTION") == "1":
        time.sleep(random.uniform(1.5, 3.0))

    date = None
    source = "None"

    # 0. URL Check
    res = check_url_source(args.keyword)
    if res and res.get('date'):
        date, source = res['date'], res['source']

    # ① GitHub Release
    if not date:
        date = check_github(args.keyword)
        if date:
            source = "GitHub"

    # ② Sonar Pro
    should_fallback = True
    if not date:
        sonar_date, should_fallback = check_sonar(args.keyword)
        if sonar_date:
            date = sonar_date
            source = "Sonar"

    # ③ Perplexity Search + GPT-4o 交叉验证 (仅在 Sonar 允许兜底时触发)
    if not date and should_fallback:
        date = check_search_gpt_fallback(args.keyword)
        if date:
            source = "GPT-4o"
    elif not date and not should_fallback:
        log("Sonar confirmed product does not exist → no fallback")

    out({'ok': True, 'release_date': date or "", 'source': source})

if __name__ == "__main__":
    main()
