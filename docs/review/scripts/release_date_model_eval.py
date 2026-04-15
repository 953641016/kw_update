#!/usr/bin/env python3
"""
release_date_model_eval.py
──────────────────────────
评测多种 LLM 在"从搜索片段中提取精准发布日期"这个兜底场景下的准确率。

方法：
  Phase 1: Serper 双查询预抓取 → 写入 JSON 快照（所有模型共享同一份上下文）
  Phase 2: 所有模型并行提取（ThreadPoolExecutor）
  Phase 3: 指标计算（准确率 / 抗幻觉率 / 格式 / 延迟）
  Phase 4: 生成中文 Markdown 报告
"""

import json, os, re, sys, time, logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── 环境 ─────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, '..', '..', '..', 'serp', 'serp_skill', '.env')
load_dotenv(ENV_PATH)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-6s %(message)s')
logger = logging.getLogger(__name__)

# ── API Keys ──
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY   = os.getenv("SERPER_API_KEY")

# ── 测试关键词 ─────────────────────────────────────────────────────────────────
TEST_KEYWORDS = [
    "ElevenMusic",
    "DynaVid",
    "Ideogram Layerize",
    "Seedance 2.0",
    "MemPalace",
    "ai music video generator",
    "Woosh",
    "Omni123",
    "SonoWorld",
    "Netflix VOID",
]

# ── Ground Truth ──
# "exact"  = 精确日期（模型输出误差 ≤ 3 天算对）
# "NULL"   = 该产品不存在 / 无公开日期 / 非具体产品（模型应输出 NULL）
# "approx" = 近似已知（仅用于参考，不参与严格计分）
GROUND_TRUTH = {
    "ElevenMusic":             {"date": "2025-08-05", "type": "exact",  "note": "ElevenLabs 发布 Eleven Music"},
    "DynaVid":                 {"date": None,         "type": "NULL",   "note": "产品不存在或极冷门，应输出 NULL"},
    "Ideogram Layerize":       {"date": None,         "type": "NULL",   "note": "功能名，无独立发布日期"},
    "Seedance 2.0":            {"date": "2026-02-12", "type": "exact",  "note": "字节跳动 Seedance 2.0 发布"},
    "MemPalace":               {"date": None,         "type": "NULL",   "note": "极冷门项目，搜索结果不一致"},
    "ai music video generator":{"date": None,         "type": "NULL",   "note": "宽泛品类词，非具体产品，必须输出 NULL"},
    "Woosh":                   {"date": None,         "type": "NULL",   "note": "产品不存在或同名冲突"},
    "Omni123":                 {"date": None,         "type": "NULL",   "note": "产品不存在"},
    "SonoWorld":               {"date": None,         "type": "NULL",   "note": "产品不存在或极冷门"},
    "Netflix VOID":            {"date": None,         "type": "NULL",   "note": "Netflix 节目，非 AI 产品"},
}

# ── 模型列表（与 V2 竞品评测一致） ─────────────────────────────────────────────
MODELS = [
    ("gpt-4o",              "openai"),
    ("gpt-4o-mini",         "openai"),
    ("gpt-5.4",             "openai"),
    ("gpt-5.1",             "openai"),
    ("gpt-5.2-pro",         "openai"),
    ("claude-sonnet-4-6",   "anthropic"),
    ("claude-opus-4-6",     "anthropic"),
    ("gemini-2.5-flash",    "gemini"),
    ("gemini-3.1-pro-preview", "gemini"),
    ("gemini-3-flash-preview", "gemini"),
]

# ── System Prompt（复用 sonar_lib.py 中的 _EXTRACT_SYSTEM） ───────────────────
EXTRACT_SYSTEM = (
    "You are an expert AI product historian. Your task is to find the VERY FIRST date when a specific "
    "AI product/model became publicly known.\n\n"
    "CRITICAL RULES:\n"
    "1. Find the EARLIEST date when THIS EXACT product first appeared publicly — whether as a beta, "
    "preview, official release, announcement, or paper. Whichever happened FIRST is the answer.\n"
    "2. If the product name includes a version (e.g. 'DeepSeek-V3'), find the date for THAT specific "
    "version, NOT any earlier or later version.\n"
    "3. VERSION DISAMBIGUATION: The FULL product name must match. 'Claude 4.5' ≠ 'Claude 4.6'. "
    "If no search result mentions the EXACT full name, output NULL.\n"
    "4. EXISTENCE CHECK: If search results do NOT contain clear direct evidence this EXACT product "
    "exists, output NULL. Do NOT infer from a predecessor.\n"
    "5. Do NOT hallucinate or guess. If unsure, output NULL.\n\n"
    "OUTPUT FORMAT: One line of reasoning, then on a new line the date ONLY:\n"
    "- YYYY-MM-DD if exact day known\n"
    "- NULL if no reliable date or product does not exist\n\n"
    "Example:\nChatGPT public preview launched November 30, 2022.\n2022-11-30"
)

DATE_RE = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')

# ── Serper 搜索 ──────────────────────────────────────────────────────────────
def serper_search(query):
    import httpx
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://google.serper.dev/search",
                headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'},
                json={'q': query, 'num': 5, 'hl': 'en', 'gl': 'us'},
            )
            resp.raise_for_status()
            data = resp.json()
            return [{'title': r.get('title',''), 'url': r.get('link',''), 'snippet': r.get('snippet','')}
                    for r in data.get('organic', [])[:5]]
    except Exception as e:
        logger.error(f"Serper error: {e}")
        return []


def format_snippets(results: list[dict]) -> str:
    parts = []
    for i, r in enumerate(results):
        parts.append(f"[{i+1}] {r['title']} ({r['url']})\n{r['snippet']}")
    return "\n\n".join(parts)


# ── LLM 调用层 ────────────────────────────────────────────────────────────────

def call_openai(model: str, messages: list[dict]) -> str:
    import httpx
    proxy = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
    client_kwargs = {"timeout": 60.0}
    if proxy:
        client_kwargs["proxy"] = proxy
    # 新版 GPT-5.x 使用 max_completion_tokens
    body = {"model": model, "messages": messages, "temperature": 0.0}
    if any(model.startswith(p) for p in ('gpt-5', 'o1', 'o3', 'o4')):
        body["max_completion_tokens"] = 200
    else:
        body["max_tokens"] = 150
    with httpx.Client(**client_kwargs) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def call_anthropic(model: str, messages: list[dict]) -> str:
    import httpx
    system_msg = ""
    user_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            user_msgs.append(m)
    proxy = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
    client_kwargs = {"timeout": 60.0}
    if proxy:
        client_kwargs["proxy"] = proxy
    with httpx.Client(**client_kwargs) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": model, "system": system_msg, "messages": user_msgs,
                  "max_tokens": 150, "temperature": 0.0},
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


def call_gemini(model: str, messages: list[dict]) -> str:
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    # 将 system + user 合并
    system_text = ""
    user_text = ""
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        else:
            user_text = m["content"]
    resp = client.models.generate_content(
        model=model,
        contents=user_text,
        config={"system_instruction": system_text, "temperature": 0.0, "max_output_tokens": 150},
    )
    return resp.text


def call_llm(model: str, provider: str, messages: list[dict]) -> str:
    if provider == "openai":
        return call_openai(model, messages)
    elif provider == "anthropic":
        return call_anthropic(model, messages)
    elif provider == "gemini":
        return call_gemini(model, messages)
    raise ValueError(f"Unknown provider: {provider}")


# ── 核心评测逻辑 ──────────────────────────────────────────────────────────────

def extract_date_from_response(text: str):
    """从 LLM 回复中提取日期或 NULL -> str or None"""
    if not text:
        return None
    text_upper = text.strip().upper()
    # 检查 NULL（出现在任何位置）
    # 先检查是否有日期，如果有日期则日期优先
    m = DATE_RE.search(text)
    if m:
        date_str = m.group(1)
        # 但如果最后一行明确写 NULL，则以 NULL 为准
        last_line = text.strip().split('\n')[-1].strip().upper()
        if last_line == 'NULL':
            return "NULL"
        return date_str
    # 无日期，检查 NULL
    if 'NULL' in text_upper or 'NO RELIABLE DATE' in text_upper or 'DOES NOT EXIST' in text_upper:
        return "NULL"
    return None


def eval_one_keyword(model_name, provider, kw, kw_cache):
    """评测单个 (模型, 关键词) 组合"""
    snippets_text = kw_cache["snippets_combined"]

    messages = [
        {"role": "system", "content": EXTRACT_SYSTEM},
        {"role": "user", "content": f"Product: {kw}\n\nSearch Results:\n{snippets_text[:3000]}"},
    ]

    t0 = time.time()
    try:
        raw_response = call_llm(model_name, provider, messages)
        latency = time.time() - t0
        extracted = extract_date_from_response(raw_response)
    except Exception as e:
        logger.error(f"  [{model_name}] Error on {kw}: {e}")
        raw_response = str(e)
        latency = time.time() - t0
        extracted = None

    return kw, {
        "extracted": extracted,
        "raw_response": raw_response[:200] if raw_response else "",
        "latency": latency,
    }


def eval_one_model(model_name, provider, cache, keywords):
    """评测单个模型的所有关键词（3 路并发）"""
    logger.info(f"  ▶ 开始评测: {model_name}")
    model_results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        for kw in keywords:
            fut = pool.submit(eval_one_keyword, model_name, provider, kw, cache[kw])
            futures[fut] = kw
        for fut in as_completed(futures):
            kw, result = fut.result()
            model_results[kw] = result
            logger.info(f"  [{model_name}] {kw}: extracted={result['extracted']}, latency={result['latency']:.1f}s")
    logger.info(f"  ✅ {model_name} 完成")
    return model_name, model_results


# ── 指标计算 ──────────────────────────────────────────────────────────────────

def calc_metrics(model_results: dict) -> dict:
    """计算一个模型的汇总指标"""
    total = 0
    correct_date = 0    # 日期准确（误差 ≤ 3 天）
    correct_null = 0    # 正确输出 NULL
    false_positive = 0  # GT 是 NULL 但模型瞎编了日期
    total_null_gt = 0   # GT 为 NULL 的总数
    total_date_gt = 0   # GT 有日期的总数
    total_latency = 0
    format_ok = 0

    for kw, result in model_results.items():
        gt = GROUND_TRUTH.get(kw, {})
        gt_type = gt.get("type", "NULL")
        gt_date = gt.get("date")
        extracted = result.get("extracted")
        total_latency += result.get("latency", 0)
        total += 1

        # 格式检查
        if extracted is not None:
            format_ok += 1

        if gt_type == "NULL":
            total_null_gt += 1
            if extracted == "NULL" or extracted is None:
                correct_null += 1
            else:
                false_positive += 1
        elif gt_type == "exact" and gt_date:
            total_date_gt += 1
            if extracted and extracted != "NULL":
                try:
                    d_ext = datetime.strptime(extracted, "%Y-%m-%d")
                    d_gt = datetime.strptime(gt_date, "%Y-%m-%d")
                    if abs((d_ext - d_gt).days) <= 3:
                        correct_date += 1
                except:
                    pass

    anti_hallucination = correct_null / total_null_gt if total_null_gt else 0
    date_accuracy = correct_date / total_date_gt if total_date_gt else 0
    overall = (correct_date + correct_null) / total if total else 0

    return {
        "overall_accuracy": overall,
        "date_accuracy": date_accuracy,
        "anti_hallucination": anti_hallucination,
        "correct_date": correct_date,
        "total_date_gt": total_date_gt,
        "correct_null": correct_null,
        "total_null_gt": total_null_gt,
        "false_positive": false_positive,
        "format_rate": format_ok / total if total else 0,
        "avg_latency": total_latency / total if total else 0,
    }


# ── 报告生成 ──────────────────────────────────────────────────────────────────

def generate_report(results: dict, cache: dict):
    report_path = os.path.join(SCRIPT_DIR, "..", "发布日期兜底模型评测报告.md")
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append("# 发布日期兜底模型评测报告\n")
    lines.append(f"> 评测时间: {now}")
    lines.append(f"> 测试关键词: {len(TEST_KEYWORDS)} 个")
    lines.append(f"> 参赛模型: {len(MODELS)} 个")
    lines.append("> 场景: Sonar 阶段1返回 date_unknown 后，Serper + LLM 兜底提取发布日期")
    lines.append("> 方法: 预抓取 Serper 搜索快照 → 所有模型读同一份上下文 → 对比 Ground Truth\n")

    # ── 总览排名 ──
    lines.append("## 一、总览排名\n")
    header = "| 排名 | 模型 | 综合准确率 | 日期准确率 | 抗幻觉率 | 误报数 | 格式通过率 | 平均延迟 |"
    sep    = "|---|---|---|---|---|---|---|---|"
    lines.append(header)
    lines.append(sep)

    # 排序
    scored = []
    for model_name, model_results in results.items():
        m = calc_metrics(model_results)
        scored.append((model_name, m))
    scored.sort(key=lambda x: (-x[1]["date_accuracy"], -x[1]["anti_hallucination"], -x[1]["overall_accuracy"], x[1]["avg_latency"]))

    medals = ["🥇", "🥈", "🥉"]
    for i, (model_name, m) in enumerate(scored):
        rank = medals[i] if i < 3 else str(i + 1)
        lines.append(
            f"| {rank} | **{model_name}** "
            f"| {m['overall_accuracy']:.0%} "
            f"| {m['date_accuracy']:.0%} ({m['correct_date']}/{m['total_date_gt']}) "
            f"| {m['anti_hallucination']:.0%} ({m['correct_null']}/{m['total_null_gt']}) "
            f"| {m['false_positive']} "
            f"| {m['format_rate']:.0%} "
            f"| {m['avg_latency']:.1f}s |"
        )

    # ── 指标说明 ──
    lines.append("\n### 指标说明\n")
    lines.append("| 指标 | 含义 | 重要性 |")
    lines.append("|---|---|---|")
    lines.append("| 综合准确率 | (日期答对 + NULL 答对) / 总词数 | ⭐⭐⭐⭐ |")
    lines.append("| 日期准确率 | 有 GT 日期的关键词中，模型提取日期误差 ≤ 3 天的比例 | ⭐⭐⭐⭐⭐ |")
    lines.append("| 抗幻觉率 | GT 为 NULL 时，模型正确输出 NULL 的比例（越高越安全）| ⭐⭐⭐⭐⭐ |")
    lines.append("| 误报数 | GT 为 NULL 但模型瞎编了日期的次数（越低越好）| ⭐⭐⭐⭐ |")
    lines.append("| 格式通过率 | 模型输出能被解析为日期或 NULL 的比例 | ⭐⭐ |")
    lines.append("| 平均延迟 | 单次 LLM 调用耗时 | ⭐⭐ |")

    lines.append("\n---\n")

    # ── 逐关键词详细对比 ──
    lines.append("## 二、逐关键词详细对比\n")

    # 表头
    model_names = [m for m, _ in MODELS]
    short_names = []
    for mn in model_names:
        sn = mn.replace("claude-sonnet-4-6", "c-sonnet").replace("claude-opus-4-6", "c-opus")
        sn = sn.replace("gemini-2.5-flash", "g-2.5-flash").replace("gemini-3.1-pro-preview", "g-3.1-pro")
        sn = sn.replace("gemini-3-flash-preview", "g-3-flash")
        short_names.append(sn)

    header_cols = ["关键词", "GT"] + short_names
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "---|" * len(header_cols))

    for kw in TEST_KEYWORDS:
        gt = GROUND_TRUTH.get(kw, {})
        gt_date = gt.get("date") or "NULL"
        gt_display = gt_date if gt_date != "NULL" else "❌NULL"

        row = [f"`{kw}`", f"**{gt_display}**"]

        for model_name in model_names:
            if model_name in results and kw in results[model_name]:
                ext = results[model_name][kw].get("extracted")
                if ext is None:
                    ext_display = "⚠️解析失败"
                elif ext == "NULL":
                    if gt_date == "NULL":
                        ext_display = "✅NULL"
                    else:
                        ext_display = "❌NULL"
                else:
                    if gt_date == "NULL":
                        ext_display = f"❌{ext}"
                    else:
                        try:
                            d_ext = datetime.strptime(ext, "%Y-%m-%d")
                            d_gt = datetime.strptime(gt_date, "%Y-%m-%d")
                            if abs((d_ext - d_gt).days) <= 3:
                                ext_display = f"✅{ext}"
                            else:
                                ext_display = f"❌{ext}"
                        except:
                            ext_display = f"❌{ext}"
            else:
                ext_display = "—"
            row.append(ext_display)

        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n---\n")

    # ── GT 说明 ──
    lines.append("## 三、Ground Truth 说明\n")
    lines.append("| 关键词 | GT 日期 | 类型 | 说明 |")
    lines.append("|---|---|---|---|")
    for kw in TEST_KEYWORDS:
        gt = GROUND_TRUTH.get(kw, {})
        lines.append(f"| {kw} | {gt.get('date') or 'NULL'} | {gt.get('type','')} | {gt.get('note','')} |")

    lines.append("\n---\n")

    # ── 已知发现 ──
    lines.append("## 四、已知发现\n")
    lines.append("（评测完成后由脚本自动生成，请参考上方数据手动补充分析。）\n")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    logger.info(f"\n📄 报告已保存: {report_path}")


# ── 主函数 ────────────────────────────────────────────────────────────────────

SNAPSHOT_PATH = os.path.join(SCRIPT_DIR, "release_date_serper_snapshot.json")


def main():
    # ── Phase 1: Serper 双查询预抓取 ──
    if os.path.exists(SNAPSHOT_PATH):
        logger.info(f"📦 Phase 1: 发现已有快照 {SNAPSHOT_PATH}，跳过搜索")
        with open(SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    else:
        logger.info(f"🔍 Phase 1: 开始 Serper 双查询预抓取 ({len(TEST_KEYWORDS)} 个关键词)")
        cache = {}
        for kw in TEST_KEYWORDS:
            logger.info(f"  Searching: {kw}")
            q1 = f'"{kw}" release date'
            q2 = f'"{kw}" official launch announcement'
            r1 = serper_search(q1)
            time.sleep(0.5)
            r2 = serper_search(q2)
            time.sleep(0.5)

            snippets1 = format_snippets(r1)
            snippets2 = format_snippets(r2)
            combined = f"=== Query 1: {q1} ===\n{snippets1}\n\n=== Query 2: {q2} ===\n{snippets2}"

            cache[kw] = {
                "query1": q1,
                "query2": q2,
                "results_q1": r1,
                "results_q2": r2,
                "snippets_combined": combined,
            }
            logger.info(f"    q1={len(r1)} results, q2={len(r2)} results")

        with open(SNAPSHOT_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"  💾 快照已保存: {SNAPSHOT_PATH}")

    # ── Phase 2: 并行模型评测（OpenAI 限 2 并发防 429） ──
    results = {}
    total_models = len(MODELS)

    # 分组：非 OpenAI 全并行，OpenAI 限 2 并发
    non_openai = [(m, p) for m, p in MODELS if p != "openai"]
    openai_models = [(m, p) for m, p in MODELS if p == "openai"]

    logger.info(f"\n🚀 Phase 2: 启动 {total_models} 个模型评测 (非OpenAI {len(non_openai)} 并行 + OpenAI {len(openai_models)} 限2并发)")

    # 第一波：非 OpenAI 全并行
    with ThreadPoolExecutor(max_workers=len(non_openai)) as pool:
        futures = {}
        for model_name, provider in non_openai:
            fut = pool.submit(eval_one_model, model_name, provider, cache, TEST_KEYWORDS)
            futures[fut] = model_name
        for fut in as_completed(futures):
            model_name, model_results = fut.result()
            results[model_name] = model_results
            logger.info(f"  🏁 [{model_name}] 评测完成 ({len(results)}/{total_models})")

    # 第二波：OpenAI 限 2 并发（5 模型 × 3 关键词并发 = 最多 6 并发 API 调用）
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        for model_name, provider in openai_models:
            fut = pool.submit(eval_one_model, model_name, provider, cache, TEST_KEYWORDS)
            futures[fut] = model_name
        for fut in as_completed(futures):
            model_name, model_results = fut.result()
            results[model_name] = model_results
            logger.info(f"  🏁 [{model_name}] 评测完成 ({len(results)}/{total_models})")

    logger.info(f"\n✅ Phase 2 完成: 全部 {total_models} 个模型评测结束")

    # ── Phase 3 & 4: 指标计算 + 报告生成 ──
    generate_report(results, cache)


if __name__ == "__main__":
    main()
