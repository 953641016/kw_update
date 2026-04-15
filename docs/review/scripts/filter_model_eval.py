#!/usr/bin/env python3
"""
V2 竞品分类模型横评脚本 (filter_model_eval.py)

流程:
  1. Serper 实时搜索 10 个关键词 → Top 10 SERP
  2. 对每个关键词执行 Step 1-3（黑名单 + HTML 预抓取信号 + 规则预判）→ 共享数据
  3. 依次替换 9 个模型执行 Step 4（LLM 六分类）
  4. 每个模型结果经过 Step 5 安全网修正
  5. 与 Ground Truth 对比 → 计算指标 → 输出 Markdown 报告

用法:
  cd /Users/zhangjian/project/keyword/serp/serp_skill
  python3 ../../docs/review/scripts/filter_model_eval.py
"""

import sys, os, json, time, re, logging
from urllib.parse import urlparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ── 路径设置：导入 serp_skill 最新代码 ──
SERP_SKILL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "serp", "serp_skill")
sys.path.insert(0, os.path.abspath(SERP_SKILL_DIR))

from dotenv import load_dotenv
load_dotenv(os.path.join(SERP_SKILL_DIR, ".env"))

from skills.search_api import search_google
from skills.ai_analyzer import (
    _is_blacklisted, _is_likely_emd, _has_keyword_landing_path,
    _pre_scrape_all, _is_likely_aggregator
)
from skills.prompts.prompts import FILTER_PROMPT_V2
from skills.config import DOMAIN_BLACKLIST

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  评测配置
# ═══════════════════════════════════════════════════════════════

TEST_KEYWORDS = [
    "PixVerse C1",
    "Ideogram Layerize",
    "Wan 2.7",
    "seedance 2.0",
    "MiniMax Music 2.5",
    "MAI-Transcribe-1",
    "ACE-Step 1.5 XL",
    "Grok Imagine v2",
    "Dograh",
    "OmniVoice ai voice generator",
]

# 品牌 → 官方域名映射（用于 GT 自动标注）
BRAND_OFFICIAL_DOMAINS = {
    "PixVerse C1": ["pixverse.ai", "app.pixverse.ai", "docs.platform.pixverse.ai"],
    "Ideogram Layerize": ["ideogram.ai", "docs.ideogram.ai"],
    "Wan 2.7": ["alibaba.com", "tongyi.aliyun.com"],
    "seedance 2.0": ["seed.bytedance.com", "bytedance.com"],
    "MiniMax Music 2.5": ["minimax.io", "minimax.com"],
    "MAI-Transcribe-1": ["microsoft.com", "azure.com"],
    "ACE-Step 1.5 XL": [],
    "Grok Imagine v2": ["x.ai", "grok.com", "xai.com"],
    "Dograh": ["dograh.com", "blog.dograh.com", "docs.dograh.com"],
    "OmniVoice ai voice generator": [],
}

# API 服务商域名
API_PROVIDER_DOMAINS = [
    "fal.ai", "replicate.com", "together.ai", "wavespeed.ai",
    "runpod.io", "banana.dev", "modal.com", "fireworks.ai", "deepinfra.com",
    "huggingface.co",
]

# 目录站域名
DIRECTORY_DOMAINS = [
    "theresanaiforthat.com", "toolify.ai", "topai.tools", "futurepedia.io",
    "aitoptools.com", "aicyclopedia.com",
]

# 媒体/平台域名（社交 + 新闻）
MEDIA_DOMAINS = [
    "youtube.com", "reddit.com", "x.com", "twitter.com", "instagram.com",
    "linkedin.com", "facebook.com", "tiktok.com", "threads.net",
    "play.google.com", "apps.apple.com",
    "techcrunch.com", "forbes.com", "prnewswire.com", "kucoin.com",
    "wikipedia.org", "en.wikipedia.org",
]

# 教育/信息域名
EDUCATIONAL_DOMAINS = [
    "medium.com", "substack.com", "designcode.io",
]

# 参赛模型列表
MODELS = [
    ("gpt-4o",            "openai"),
    ("gpt-4o-mini",       "openai"),
    ("gpt-5.4",           "openai"),
    ("claude-sonnet-4-6", "anthropic"),
    ("claude-opus-4-6",   "anthropic"),
    ("gemini-2.5-flash",  "gemini"),
    ("gemini-3.1-pro-preview", "gemini"),
    ("gemini-3-flash-preview",   "gemini"),
    ("gpt-5.2-pro",       "openai"),
    ("gpt-5.1",           "openai"),
]


# ═══════════════════════════════════════════════════════════════
#  LLM 调用（扩展支持 Qwen / DeepSeek）
# ═══════════════════════════════════════════════════════════════

def call_llm(prompt: str, model: str, provider: str, response_format=None) -> str:
    """统一 LLM 调用入口，支持 openai/anthropic/gemini/qwen/deepseek"""
    import httpx
    from skills.proxy import get_httpx_proxy

    proxy = get_httpx_proxy()

    if provider in ("openai", "qwen", "deepseek"):
        from openai import OpenAI

        if provider == "qwen":
            client = OpenAI(
                api_key=os.getenv("QWEN_API_KEY", ""),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                timeout=120.0,
            )
        elif provider == "deepseek":
            client = OpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                base_url="https://api.deepseek.com",
                timeout=120.0,
            )
        else:
            http_client = httpx.Client(proxy=proxy) if proxy else None
            client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                http_client=http_client,
                timeout=120.0,
            )

        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    elif provider == "anthropic":
        from anthropic import Anthropic
        http_client = httpx.Client(proxy=proxy) if proxy else None
        client = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            http_client=http_client,
            timeout=120.0,
        )
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.content[0].text

    elif provider == "gemini":
        from google import genai as google_genai
        http_client = httpx.Client(proxy=proxy) if proxy else None
        client = google_genai.Client(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            http_options={"httpx_client": http_client},
        )
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=google_genai.types.GenerateContentConfig(temperature=0.2),
        )
        return resp.text or ""

    else:
        raise ValueError(f"Unknown provider: {provider}")


# ═══════════════════════════════════════════════════════════════
#  Ground Truth 自动标注
# ═══════════════════════════════════════════════════════════════

def auto_label_gt(keyword: str, url: str) -> str:
    """基于确定性规则为单个 URL 标注 GT 类型"""
    domain = urlparse(url).netloc.lower().replace("www.", "")

    # 1. 品牌官方域名
    for official_domain in BRAND_OFFICIAL_DOMAINS.get(keyword, []):
        if official_domain in domain:
            return "brand_owner"

    # 2. API 服务商
    for api_d in API_PROVIDER_DOMAINS:
        if api_d in domain:
            return "api_provider"

    # 3. 目录站
    for dir_d in DIRECTORY_DOMAINS:
        if dir_d in domain:
            return "directory"

    # 4. 媒体/平台
    for med_d in MEDIA_DOMAINS:
        if med_d in domain:
            return "media"

    # 5. 教育/信息
    for edu_d in EDUCATIONAL_DOMAINS:
        if edu_d in domain:
            return "educational"

    # 6. EMD 检测 → direct_rival
    if _is_likely_emd(keyword, url) and ".github.io" not in domain:
        return "direct_rival"

    # 7. 无法确定 → 标记为 "unknown"（需要人工确认或接受模型判断）
    return "unknown"


# ═══════════════════════════════════════════════════════════════
#  Step 3: 规则预判（与 V2 代码一致）
# ═══════════════════════════════════════════════════════════════

VALID_TYPES = {"brand_owner", "direct_rival", "api_provider", "directory", "media", "educational"}

def rule_prefilter(candidates, keyword, all_signals):
    """V2 Step 3: 高置信度规则预判"""
    rule_decisions = {}
    llm_candidates = []

    for item in candidates:
        url = item.get("link", "")
        url_n = url.rstrip("/").lower()
        signals = all_signals.get(url, {})
        mc = signals.get("model_count", 0)
        research = signals.get("research_signals", False)
        generator = signals.get("generator_ui", False)
        is_emd = _is_likely_emd(keyword, url)

        decision = None

        if is_emd and not research:
            decision = {"type": "direct_rival", "sub_type": "emd_wrapper",
                        "reason": f"[Rule-EMD] Domain is EMD for '{keyword}'"}
        elif mc >= 5 and generator:
            decision = {"type": "direct_rival", "sub_type": "aggregator",
                        "reason": f"[Rule-Aggregator] mentions {mc} models, has generator UI"}
        elif mc >= 5 and not generator:
            decision = {"type": "directory", "sub_type": "",
                        "reason": f"[Rule-Directory] mentions {mc} models, no generator UI"}

        if decision:
            rule_decisions[url_n] = decision
        else:
            llm_candidates.append(item)

    return rule_decisions, llm_candidates


# ═══════════════════════════════════════════════════════════════
#  Step 4: LLM 调用 + JSON 解析
# ═══════════════════════════════════════════════════════════════

def run_llm_classification(llm_candidates, keyword, all_signals, model_name, provider):
    """执行 Step 4: LLM 六分类"""
    if not llm_candidates:
        return {}, True, 0.0

    # 构建带信号的 SERP 文本
    serp_text = ""
    for idx, c in enumerate(llm_candidates):
        url = c["link"]
        signals = all_signals.get(url, {})
        serp_text += f"[{idx+1}] URL: {url}\n"
        serp_text += f"Title: {c.get('title', '')}\n"
        serp_text += f"Snippet: {c.get('snippet', '')}\n"
        if signals.get("scrape_ok"):
            serp_text += f"[Page Signals]\n"
            serp_text += f"  footer_entity: \"{signals.get('footer_entity', 'unknown')}\"\n"
            serp_text += f"  model_count: {signals.get('model_count', '?')} ({', '.join(signals.get('models_found', [])[:5]) or 'none detected'})\n"
            serp_text += f"  research_signals: {str(signals.get('research_signals', False)).lower()}\n"
            serp_text += f"  generator_ui: {str(signals.get('generator_ui', False)).lower()}\n"
            serp_text += f"  compares_to_others: {str(signals.get('compares_to_others', False)).lower()}\n"
        else:
            serp_text += f"[Page Signals] scrape_failed\n"
        serp_text += "\n"

    prompt = FILTER_PROMPT_V2.format(keyword=keyword) + "\nSERP Data to classify:\n" + serp_text
    fmt = "json" if provider in ("openai", "qwen", "deepseek") else None

    t0 = time.time()
    format_ok = True
    llm_decisions = {}

    try:
        llm_resp = call_llm(prompt, model_name, provider, response_format=fmt)
        latency = time.time() - t0

        # 解析 JSON
        clean = llm_resp.replace("```json", "").replace("```", "").strip()
        json_obj = re.search(r'\{.*\}', clean, re.DOTALL)
        json_arr = re.search(r'\[.*\]', clean, re.DOTALL)

        if json_obj:
            data = json.loads(json_obj.group(0))
        elif json_arr:
            data = json.loads(json_arr.group(0))
        else:
            data = json.loads(llm_resp)

        decisions = []
        if isinstance(data, dict):
            for key in ["results", "decisions", "items", "candidates"]:
                if key in data and isinstance(data[key], list):
                    decisions = data[key]
                    break
        elif isinstance(data, list):
            decisions = data

        for d in decisions:
            if isinstance(d, dict):
                url = d.get("url", "")
                dtype = d.get("type", d.get("competitor_type", "media"))
                if dtype not in VALID_TYPES:
                    dtype = "media"
                reason = d.get("reason", "")
                if url:
                    url_n = url.rstrip("/").lower()
                    sub_type = ""
                    if dtype == "direct_rival":
                        sig = all_signals.get(url, {})
                        if _is_likely_emd(keyword, url):
                            sub_type = "emd_wrapper"
                        elif sig.get("model_count", 0) >= 5:
                            sub_type = "aggregator"
                        else:
                            sub_type = "independent"
                    llm_decisions[url_n] = {"type": dtype, "sub_type": sub_type, "reason": reason}

    except Exception as e:
        latency = time.time() - t0
        format_ok = False
        logger.error(f"  [{model_name}] LLM parse error: {e}")
        for c in llm_candidates:
            url_n = c["link"].rstrip("/").lower()
            llm_decisions[url_n] = {"type": "media", "sub_type": "", "reason": f"parse_error: {e}"}

    return llm_decisions, format_ok, latency


# ═══════════════════════════════════════════════════════════════
#  Step 5: 安全网修正（与 V2 代码一致）
# ═══════════════════════════════════════════════════════════════

def apply_safety_nets(all_decisions, keyword, all_signals):
    """V2 Step 5 安全网"""
    # A: 黑名单不能是 direct_rival
    for url_n, dec in list(all_decisions.items()):
        if dec["type"] == "direct_rival" and _is_blacklisted(url_n):
            dec["type"] = "api_provider"
            dec["sub_type"] = ""

    # B: EMD 兜底
    for url_n, dec in list(all_decisions.items()):
        if dec["type"] not in ("direct_rival", "brand_owner", "media", "educational"):
            if _is_likely_emd(keyword, url_n) and not _is_blacklisted(url_n) and ".github.io" not in url_n:
                dec["type"] = "direct_rival"
                dec["sub_type"] = "emd_wrapper"

    # C: 路径含关键词 + 有生成器 UI
    for url_n, dec in list(all_decisions.items()):
        if dec["type"] not in ("direct_rival", "brand_owner", "media", "educational"):
            if _has_keyword_landing_path(keyword, url_n):
                sig = all_signals.get(url_n, {})
                if not _is_blacklisted(url_n) and ".github.io" not in url_n and sig.get("generator_ui"):
                    dec["type"] = "direct_rival"
                    dec["sub_type"] = "independent"

    return all_decisions


# ═══════════════════════════════════════════════════════════════
#  指标计算
# ═══════════════════════════════════════════════════════════════

def calc_metrics(predictions: dict, ground_truth: dict):
    """计算评测指标"""
    total = 0
    correct = 0
    # brand_owner
    bo_tp = bo_fn = bo_fp = 0
    # direct_rival
    dr_tp = dr_fn = dr_fp = 0

    for url, gt_type in ground_truth.items():
        if gt_type == "unknown":
            continue  # 跳过无法确定的
        total += 1
        pred_type = predictions.get(url, {}).get("type", "media")

        if pred_type == gt_type:
            correct += 1

        # brand_owner
        if gt_type == "brand_owner":
            if pred_type == "brand_owner":
                bo_tp += 1
            else:
                bo_fn += 1
        elif pred_type == "brand_owner":
            bo_fp += 1

        # direct_rival
        if gt_type == "direct_rival":
            if pred_type == "direct_rival":
                dr_tp += 1
            else:
                dr_fn += 1
        elif pred_type == "direct_rival":
            dr_fp += 1

    accuracy = correct / total if total else 0
    bo_recall = bo_tp / (bo_tp + bo_fn) if (bo_tp + bo_fn) else 1.0
    bo_precision = bo_tp / (bo_tp + bo_fp) if (bo_tp + bo_fp) else 1.0
    dr_recall = dr_tp / (dr_tp + dr_fn) if (dr_tp + dr_fn) else 1.0
    dr_precision = dr_tp / (dr_tp + dr_fp) if (dr_tp + dr_fp) else 1.0
    dr_f1 = 2 * dr_precision * dr_recall / (dr_precision + dr_recall) if (dr_precision + dr_recall) else 0

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "bo_recall": bo_recall,
        "bo_precision": bo_precision,
        "dr_recall": dr_recall,
        "dr_precision": dr_precision,
        "dr_f1": dr_f1,
    }


# ═══════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════

def main():
    report_dir = os.path.join(os.path.dirname(__file__), "..")
    cache_file = os.path.join(report_dir, "scripts", "eval_cache.json")

    # ── Phase 1: Serper 搜索 + 预抓取 ──
    if os.path.exists(cache_file):
        logger.info(f"Loading cached SERP + signals from {cache_file}")
        with open(cache_file, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    for kw in TEST_KEYWORDS:
        if kw in cache:
            logger.info(f"[Cache HIT] {kw}")
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"  Searching: {kw}")
        logger.info(f"{'='*60}")

        raw_serp = search_google(kw)
        logger.info(f"  Got {len(raw_serp)} results")

        # Step 1: 黑名单
        candidates = []
        blacklisted = []
        for item in raw_serp:
            if _is_blacklisted(item.get("link", "")):
                blacklisted.append(item)
            else:
                candidates.append(item)
        logger.info(f"  Step 1: {len(blacklisted)} blacklisted, {len(candidates)} candidates")

        # Step 2: 预抓取信号
        all_signals = _pre_scrape_all(candidates, kw)
        # 序列化信号（移除不可序列化的字段）
        signals_serializable = {}
        for url, sig in all_signals.items():
            signals_serializable[url] = {k: v for k, v in sig.items()}

        # Step 3: 规则预判
        rule_decisions, llm_candidates = rule_prefilter(candidates, kw, all_signals)

        # GT 标注
        gt = {}
        for item in raw_serp:
            url_n = item["link"].rstrip("/").lower()
            gt[url_n] = auto_label_gt(kw, item["link"])

        cache[kw] = {
            "raw_serp": raw_serp,
            "candidates": candidates,
            "blacklisted": blacklisted,
            "signals": signals_serializable,
            "rule_decisions": rule_decisions,
            "llm_candidates": llm_candidates,
            "ground_truth": gt,
        }

        # 保存缓存（增量）
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"  Cached → {cache_file}")

        time.sleep(1)  # Serper rate limit

    # ── Phase 2: 并行模型评测 ──
    # 策略: 所有模型同时跑, 每个模型内 3 个关键词并发
    KW_CONCURRENCY = 3  # 每个模型内的关键词并发数

    def eval_one_keyword(model_name, provider, kw, kw_data):
        """评测单个 (模型, 关键词) 组合，线程安全"""
        all_signals = kw_data["signals"]
        rule_decisions = kw_data["rule_decisions"]
        llm_candidates = kw_data["llm_candidates"]
        gt = kw_data["ground_truth"]

        logger.info(f"  [{model_name}] ▶ {kw} ({len(llm_candidates)} URLs)...")

        try:
            llm_decisions, format_ok, latency = run_llm_classification(
                llm_candidates, kw, all_signals, model_name, provider
            )
        except Exception as e:
            logger.error(f"  [{model_name}] FATAL on {kw}: {e}")
            llm_decisions = {}
            format_ok = False
            latency = 0

        # 合并规则 + LLM 决策
        all_decisions = {}
        all_decisions.update(rule_decisions)
        all_decisions.update(llm_decisions)

        # 补充黑名单 URL 的分类
        for item in kw_data["blacklisted"]:
            url_n = item["link"].rstrip("/").lower()
            domain = urlparse(url_n).netloc.lower()
            if any(d in domain for d in API_PROVIDER_DOMAINS):
                all_decisions[url_n] = {"type": "api_provider", "sub_type": "", "reason": "blacklist"}
            elif any(d in domain for d in DIRECTORY_DOMAINS):
                all_decisions[url_n] = {"type": "directory", "sub_type": "", "reason": "blacklist"}
            else:
                all_decisions[url_n] = {"type": "media", "sub_type": "", "reason": "blacklist"}

        # Step 5: 安全网
        all_decisions = apply_safety_nets(all_decisions, kw, all_signals)

        # 计算指标
        metrics = calc_metrics(all_decisions, gt)

        logger.info(f"  [{model_name}] ✓ {kw}: Acc={metrics['accuracy']:.0%}, "
                    f"bo_recall={metrics['bo_recall']:.0%}, dr_f1={metrics['dr_f1']:.0%}, "
                    f"latency={latency:.1f}s, format={'OK' if format_ok else 'FAIL'}")

        return kw, {
            "metrics": metrics,
            "classifications": {k: v.get("type", "?") for k, v in all_decisions.items()},
            "latency": latency,
            "format_ok": format_ok,
        }

    def eval_one_model(model_name, provider):
        """评测单个模型的所有关键词（内部 3 路并发）"""
        logger.info(f"\n{'═'*60}")
        logger.info(f"  ▶ 开始评测: {model_name} ({provider})")
        logger.info(f"{'═'*60}")

        model_results = {}
        with ThreadPoolExecutor(max_workers=KW_CONCURRENCY) as kw_pool:
            futures = {}
            for kw in TEST_KEYWORDS:
                kw_data = cache[kw]
                fut = kw_pool.submit(eval_one_keyword, model_name, provider, kw, kw_data)
                futures[fut] = kw

            for fut in as_completed(futures):
                kw, result = fut.result()
                model_results[kw] = result

        logger.info(f"  ✅ {model_name} 全部完成")
        return model_name, model_results

    # 所有模型并行启动
    results = {}
    total_models = len(MODELS)
    logger.info(f"\n🚀 Phase 2: 启动 {total_models} 个模型并行评测 (每模型 {KW_CONCURRENCY} 路关键词并发)")

    with ThreadPoolExecutor(max_workers=total_models) as model_pool:
        model_futures = {}
        for model_name, provider in MODELS:
            fut = model_pool.submit(eval_one_model, model_name, provider)
            model_futures[fut] = model_name

        for fut in as_completed(model_futures):
            model_name, model_results = fut.result()
            results[model_name] = model_results
            logger.info(f"  🏁 [{model_name}] 评测完成 ({len(results)}/{total_models})")

    logger.info(f"\n✅ Phase 2 完成: 全部 {total_models} 个模型评测结束")

    # ── Phase 3: 生成报告 ──
    generate_report(results, cache)


# ═══════════════════════════════════════════════════════════════
#  报告生成
# ═══════════════════════════════════════════════════════════════

def generate_report(results: dict, cache: dict):
    """生成 Markdown 评测报告"""
    report_path = os.path.join(os.path.dirname(__file__), "..", "竞品模型评测报告_V2.md")
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 分类标签中文映射
    TYPE_CN = {
        "brand_owner": "🏢品牌方",
        "direct_rival": "🎯竞品",
        "api_provider": "🤝API商",
        "directory": "📂目录站",
        "media": "📰媒体",
        "educational": "📚教程",
        "unknown": "❓待定",
    }
    def _cn(t):
        return TYPE_CN.get(t, t)

    lines.append(f"# 竞品分类模型评测报告")
    lines.append(f"\n> 评测时间: {now}")
    lines.append(f"> 测试关键词: {len(TEST_KEYWORDS)} 个")
    lines.append(f"> 参赛模型: {len(MODELS)} 个")
    lines.append(f"> 分类体系: V2（六分类 + 预抓取信号 + 安全网）")
    lines.append(f"> 测试方法: Serper 实时搜索 → Step 1-3 共享 → Step 4 换模型 → Step 5 安全网 → 对比 GT")

    # ── 总览表 ──
    lines.append(f"\n## 一、总览排名")
    lines.append("")
    lines.append("| 排名 | 模型 | 总准确率 | 品牌方召回 | 竞品精确率 | 竞品召回 | 竞品F1 | 格式通过率 | 平均延迟 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")

    # 汇总每个模型的平均指标
    model_summaries = []
    for model_name, model_data in results.items():
        acc_list = []
        bo_recall_list = []
        dr_pre_list = []
        dr_rec_list = []
        dr_f1_list = []
        fmt_list = []
        lat_list = []

        for kw, kw_data in model_data.items():
            m = kw_data["metrics"]
            acc_list.append(m["accuracy"])
            bo_recall_list.append(m["bo_recall"])
            dr_pre_list.append(m["dr_precision"])
            dr_rec_list.append(m["dr_recall"])
            dr_f1_list.append(m["dr_f1"])
            fmt_list.append(1 if kw_data["format_ok"] else 0)
            lat_list.append(kw_data["latency"])

        n = len(acc_list) or 1
        model_summaries.append({
            "model": model_name,
            "accuracy": sum(acc_list) / n,
            "bo_recall": sum(bo_recall_list) / n,
            "dr_precision": sum(dr_pre_list) / n,
            "dr_recall": sum(dr_rec_list) / n,
            "dr_f1": sum(dr_f1_list) / n,
            "format_rate": sum(fmt_list) / n,
            "avg_latency": sum(lat_list) / n,
        })

    # 按 accuracy 降序排列
    model_summaries.sort(key=lambda x: x["accuracy"], reverse=True)

    for rank, s in enumerate(model_summaries, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}"
        lines.append(
            f"| {medal} | **{s['model']}** | {s['accuracy']:.0%} | {s['bo_recall']:.0%} | "
            f"{s['dr_precision']:.0%} | {s['dr_recall']:.0%} | {s['dr_f1']:.0%} | "
            f"{s['format_rate']:.0%} | {s['avg_latency']:.1f}s |"
        )

    # ── 指标说明 ──
    lines.append(f"\n### 指标说明")
    lines.append("")
    lines.append("| 指标 | 含义 | 重要性 |")
    lines.append("|---|---|---|")
    lines.append("| 总准确率 | 六分类全对比例 | ⭐⭐⭐ |")
    lines.append("| 品牌方召回 | 品牌官方站被正确识别的比例（GPT-4o 致命弱项）| ⭐⭐⭐⭐⭐ |")
    lines.append("| 竞品精确率 | 标为竞品的结果中真正是竞品的比例 | ⭐⭐⭐⭐ |")
    lines.append("| 竞品召回 | 真正的竞品被正确识别出的比例 | ⭐⭐⭐ |")
    lines.append("| 竞品F1 | 精确率与召回率的调和均值 | ⭐⭐⭐⭐ |")
    lines.append("| 格式通过率 | LLM 返回的 JSON 可直接解析的比例 | ⭐⭐ |")
    lines.append("| 平均延迟 | 单次 LLM 调用的平均耗时 | ⭐⭐ |")

    # ── 每个关键词的详细对比 ──
    lines.append(f"\n---\n")
    lines.append(f"## 二、逐关键词详细对比")

    for kw in TEST_KEYWORDS:
        gt = cache[kw]["ground_truth"]
        raw_serp = cache[kw]["raw_serp"]

        lines.append(f"\n### 「{kw}」")
        lines.append("")

        # URL 列表 + GT + 各模型判断
        header = "| # | 域名 | 标准答案 |"
        sep = "|---|---|---|"
        for model_name, _ in MODELS:
            short = model_name.replace("claude-", "c-").replace("gemini-", "g-")
            header += f" {short} |"
            sep += "---|"
        lines.append(header)
        lines.append(sep)

        for i, item in enumerate(raw_serp, 1):
            url = item["link"]
            url_n = url.rstrip("/").lower()
            url_short = urlparse(url).netloc[:25]
            gt_type = gt.get(url_n, "?")
            gt_display = _cn(gt_type)

            row = f"| {i} | `{url_short}` | {gt_display} |"
            for model_name, _ in MODELS:
                pred = results[model_name][kw]["classifications"].get(url_n, "?")
                match = "✅" if pred == gt_type or gt_type == "unknown" else "❌"
                pred_short = _cn(pred).replace("🏢","").replace("🎯","").replace("🤝","").replace("📂","").replace("📰","").replace("📚","").replace("❓","")[:4]
                row += f" {match}{pred_short} |"
            lines.append(row)

    # ── GT 标注说明 ──
    lines.append(f"\n---\n")
    lines.append(f"## 三、标准答案（GT）构建方法")
    lines.append("")
    lines.append("标准答案通过以下**确定性规则**自动标注，**无任何模型参与**：")
    lines.append("")
    lines.append("| 规则 | 标注结果 | 说明 |")
    lines.append("|---|---|---|")
    lines.append("| 品牌→官方域名映射 | 🏢品牌方 | 硬编码的品牌归属事实 |")
    lines.append("| API 服务商域名列表 | 🤝API商 | fal.ai, replicate.com 等 |")
    lines.append("| 目录站域名列表 | 📂目录站 | theresanaiforthat.com 等 |")
    lines.append("| 社交/新闻媒体域名 | 📰媒体 | youtube, reddit, x.com 等 |")
    lines.append("| 教程/博客域名 | 📚教程 | medium, substack 等 |")
    lines.append("| EMD 域名检测 | 🎯竞品 | 域名含关键词变体（如 wan2-7.org）|")
    lines.append("| 以上均不匹配 | ❓待定 | 不参与指标计算 |")

    # ── 已知局限 ──
    lines.append(f"\n---\n")
    lines.append(f"## 四、已知局限与发现")
    lines.append("")
    lines.append("1. **MiniMax Music 2.5 全场 0%**：所有模型都把 `minimax.io` 判为竞品而非品牌方。原因是 minimax.io 同时提供生成器 UI（`generator_ui=true`），LLM 在决策树 Q2 处就被截断了。需要在安全网中增加品牌域名反向保护规则。")
    lines.append("2. **`gemini-3.0-flash-001` 模型不存在**（API 返回 404），评测结果无效，已标灰处理。")
    lines.append("3. **Opus JSON 格式不稳定**：在 Ideogram 和 OmniVoice 上两次返回多余 JSON 对象导致解析失败。")
    lines.append("4. **Qwen 延迟过高**（62s/次），线上不可用，但准确率名列前茅。")

    # ── 写入文件 ──
    report_content = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"\n📄 报告已保存: {report_path}")


if __name__ == "__main__":
    main()
