# SEO雷达模块系统文档

## 1. 模块简介
SEO雷达是 openclaw 项目的核心内容发现与分析模块。其主要职责是每天定时从互联网上 11 个核心权威信息源全自动监控并收集全球最新的 AI 工具动态。重点覆盖 **Video, Image, Audio, Text, Agent** 五大核心品类，目的是第一时间锁定有价值的"新模型"、"预热产品"及"长尾生态词"，支撑下游 AI 导航站（jxp.com）的高效引流与占位。

收集到的候选产品与功能词，自动经过清洗、精准去重、Trends & SERP（搜索引擎结果页面）分析，并结构化写入团队的飞书多维表格。

### 运行环境
- 服务器：美国微软云 Ubuntu (2H4G)
- 模型中枢：Claude Sonnet 4.6
- 调度框架：OpenClaw Cron

### 运营数据快照（截至 2026-03-31）

| 指标 | 数值 |
|------|------|
| 关键词总库存 | 494 个 |
| 日均成本 | ~$3.55 |
| 日均新增关键词 | ~13 个 |
| 品类分布 | Text 32% / Video 29% / Audio 18% / Image 17% / Agent 3.5% |

## 2. 定时任务与数据源

系统利用 `cron` 定义了 11 个独立来源的抓取任务 + 3 个后台支持任务：

### 采集任务（按北京时间排列）

| 任务 | 时间 | 频率 | 信息源 | 平均耗时 | 效率 |
|------|------|------|--------|---------|------|
| seo-producthunt | 00:00 | 每天 | Product Hunt（近7天高赞AI新品） | ~10 min | 🔴 |
| seo-ainews | 00:02 | 每天 | 14个AI新闻站（官方博客+国际媒体+国内媒体） | ~3.6 min | 🟡 |
| seo-huggingface | 01:00 | 每天 | HuggingFace（论文+模型+Spaces） | ~8.3 min | 🟢 |
| seo-github | 02:00 | 一三五 | GitHub AI Trending（日+周） | ~1.9 min | 🟢 |
| seo-arxiv | 03:00 | 一三五 | arXiv 最新AI论文（cs.CV/LG/SD/MM, eess.AS） | ~2.8 min | 🟢 |
| seo-hackernews | 04:00 | 每天 | Hacker News 热帖（近2天） | ~2.0 min | 🔴 |
| seo-youtube | 05:00 | 每天 | YouTube Data API（5类AI视频搜索） | ~3.5 min | 🟡 |
| seo-twitter | 07:01 | 每天 | X/Twitter（11条精细化查询：官号+泄露+品类） | ~5.8 min | 🟡 |
| seo-platforms | 21:00 | 每天 | AI推理平台（fal.ai/wavespeed/replicate） | ~2.7 min | 🟢 |
| seo-china | 22:02 | 每天 | 中国大厂官方站+量子位+知乎 | ~1.9 min | 🔴 |
| seo-reddit | 23:00 | 每天 | Reddit（StableDiffusion/singularity/ML/AI_Agents） | ~1.6 min | 🟢 |

### 后台支持任务

| 任务 | 频率 | 功能 |
|------|------|------|
| weekly-report | 每周一 09:00 | 生成 SEO 雷达成本周报，发送飞书 |
| cost-flush | 每 6 小时 | 扫描 session 记录，持久化 cron 成本 |
| release-status-update | 每天 14:00 | 自动补填缺失的发布日期，更新发布状态 |

## 3. 核心数据流转机制

整个数据处理链路遵循标准化工作流，核心判读逻辑记录在 `RULES.md` 和各任务载荷中，分为 5 个阶段：

### 阶段一：数据提取 (Fetch)
- 代理使用专用爬虫脚本直接拉取源站，位于 `workspace/scripts/` 目录
- 核心脚本：`hf_papers.py`、`arxiv_fetch.py`、`ph_search.py`、`platform_watch.py`、`reddit_search.py`、`youtube_search.py`、`hn_fetch.py`
- X/Twitter 通过 `xurl` CLI + 内嵌 Python 后处理，辅以 `q2c_search.sh`、`q2d_search.sh`、`q2s_search.sh` 子脚本
- AI News 通过 web_fetch 抓取 14 个官方博客/媒体页面，OpenAI RSS 走 curl 解析
- **纪律**：严禁代理在首发拉取时私自调用 web_search，必须基于脚本返回的结构化 JSON

### 阶段二：词元识别与清洗 (Identify & Filter)
- LLM 分析提取文本（title, desc, tag），识别"正在被发布/介绍"的主角作为关键词
- 主角识别规则：找"launch/announce/release"等动词指向的名词
- 排除规则：跳过对比参照物（A > B，抛弃 B）；跳过泛词（AI Tools）；跳过竞品 SaaS 平台名（Pika/Runway/Dzine）
- **但保留大厂具体功能词**：如 Kling Elements、Runway Gen-4.5

### 阶段三：精确去重 (Dedup)
- 通过 `dedup_check.py` 脚本进行文本归一化比对和前后缀校验
- 每轮上限：普通源 5 个新词，学术源（arXiv/HF）放宽至 15 个
- 精化后关键词必须二次去重

### 阶段四：深度分析 (Analyze)
每个新词必须完成：
1. **Trends 校验**（`anchor_trends_monitor.py`）：双锚点系统查询全球搜索热度，输出 `7天均值/30天均值` 格式分数 + 趋势方向
2. **SERP 分析**（`serp_query.py`）：抓取谷歌搜索结果，统计竞品独立站数量，评估 SEO 难度
3. **发布日期获取**（`release_date_fetch.py`）：三层瀑布流架构（GitHub Release → Sonar Pro → GPT-4o），当前成功率约 57%
4. **属性界定**：划拨品类（video/image/text/audio/agent）+ 关键词类型（product/demand/technical）

### 阶段五：收尾与固化 (Delivery)
1. **飞书写入**（`write_keyword.py`）：按照严格字段定义写入飞书多维表格，同时传入媒体热度离散参数
2. **状态更新**（`update_last_task.py`）：通知调度系统任务竣工
3. **即时播报**：通过 message 通道向飞书推送当日摘要

## 4. 存储结构与状态管理

模块采用"本地轻量状态 + 云端结构化库"双轨存储设计。

### 4.1 本地状态 (`workspace/data/seo-radar-state.json`)
- **`keywords`** (List[str])：494 个已收录关键词名称，供 `dedup_check.py` 进行去重比对
- **`keyword_records`** (Dict)：关键词 → 飞书 Record ID 的映射关系
- **`counters`** (Dict)：各品类序号水位 — V:159, I:90, A:98, T:172, AG:19, HN:7
- **`keyword_media_heat`** (Dict)：本地媒体热度缓存（仅最近更新的 10 条）
- **`keyword_media_heat_peak`** (Dict)：各词的历史峰值热度
- **`lastTasks`** (Dict)：各任务最近执行时间戳
- **并发保护**：`state_io.py` 提供 `locked_state()` context manager（fcntl.LOCK_EX + 原子 rename），防止竞态条件

### 4.2 云端飞书多维表格 (TABLE_ID: `tblVZJ1xU51qTb2b`)
- **基础字段**：序号 (V-041)、关键词、收录时间、发布日期
- **分类字段**：工具类型、关键词类型 (product/demand/technical)
- **状态字段**：优先级 (高/中/低)、发布状态 (✅正式可用/🚀刚发布/📣已宣布/🔮传言泄露)
- **量化指标**：Trends分数、Trends趋势、媒体热度
- **溯源字段**：来源、来源链接
- **分析结论**：SEO分析（二段式）、SERP竞品

### 4.3 成本追踪
- **`cron-cost-log.jsonl`**：每次 cron 执行的成本记录（session_id, cron, cost, keywords, turns, ts）
- **`release-date-call-log.jsonl`**：发布日期获取的调用日志

## 5. 关键脚本清单

| 脚本 | 职责 |
|------|------|
| `RULES.md` | 所有 seo-* 任务共用的分析规范（关键词精化/去重/写入/收尾） |
| `write_keyword.py` | 核心写入脚本：去重 → 飞书创建/更新 → state 更新 → 媒体热度处理 |
| `dedup_check.py` | 精确去重：文本归一化 + 前后缀比对 |
| `anchor_trends_monitor.py` | V9 双锚点 Trends 查询系统 |
| `trends_query.py` | 旧版 Trends 查询（降级备用） |
| `serp_query.py` | Google SERP 竞品分析 |
| `release_date_fetch.py` | 三层瀑布流发布日期获取 |
| `release_status_update.py` | 每日自动补填发布状态 |
| `state_io.py` | 并发安全的 state.json 读写（锁机制） |
| `hf_papers.py` | HuggingFace 论文/模型/Spaces 抓取 |
| `arxiv_fetch.py` | arXiv 论文抓取 |
| `platform_watch.py` | AI 推理平台新模型监控 |
| `ph_search.py` | ProductHunt 搜索 |
| `reddit_search.py` | Reddit 子版块搜索 |
| `youtube_search.py` | YouTube Data API 搜索 |
| `hn_fetch.py` | Hacker News 热帖抓取 |
| `log_cost.py` | 成本日志持久化 |
| `weekly_report.py` | 周报生成 |
| `update_last_task.py` | 任务完成时间戳更新 |
