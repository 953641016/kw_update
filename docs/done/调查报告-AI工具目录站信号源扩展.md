# AI 工具目录站信号源扩展 — 调查报告

**更新时间：2026-04-01**

> 本报告调研了 7 个 AI 工具目录平台，评估其作为 SEO 雷达信号源的可行性、效果和成本。

---

## 一、调研背景

当前 SEO 雷达有 10 个信号源（HN 已砍），覆盖了学术首发（arXiv/HF）、社区讨论（Reddit/Twitter）、官方发布（AI News/中国官方站）、KOL 评测（YouTube）和推理平台上架（Platforms）等维度。

**但缺少 AI 工具目录站维度。** 大量 AI 工具（尤其中小型独立开发者产品）不走 ProductHunt / Reddit / HuggingFace，但一定会去 Toolify、TAAFT 等目录站提交以获取流量。这是当前信号源覆盖不到的「商业化工具首发」渠道。

---

## 二、需求指定的三个平台

### 2.1 Toolify.ai

| 维度 | 详情 |
|------|------|
| **平台类型** | AI 专属工具目录 |
| **收录规模** | 28,500+ AI 工具，459 品类 |
| **月访问量** | ~5M+ |
| **更新频率** | 每日（Today / New 页面）|
| **品类覆盖** | Video ✅ Image ✅ Audio ✅ Text ✅ Agent ✅ |
| **新工具入口** | `/best-ai-tools`（Today / New / Most Saved / Most Used）|
| **Sitemap** | ✅ `sitemap.xml`（多文件结构化，`sitemap_tools_1.xml` 等）|
| **RSS** | ❌ 无 |
| **API** | ❌ 无公开 API |
| **反爬保护** | ⭐ **低**（无 Cloudflare，标准网页）|
| **Jina Reader** | ⭐ **可行**（`curl -s "https://r.jina.ai/URL"` 直接返回 markdown）|
| **信噪比** | 高（纯 AI 工具，无非 AI 内容噪音）|
| **产词类型倾向** | 90%+ product 词 |
| **与现有源重叠度** | 低（~20-30% 与 PH 重叠）|
| **jxp.com 匹配度** | ⭐ **最高**（纯 AI 生成工具目录）|

**结论：⭐ 最佳信号源候选。反爬低、品类匹配度最高、Jina Reader 可直接抓取。推荐作为主力源接入。**

---

### 2.2 topai.tools

| 维度 | 详情 |
|------|------|
| **平台类型** | AI 专属工具目录 |
| **收录规模** | 120+ 品类 |
| **更新频率** | 每日 |
| **品类覆盖** | Video ✅ Image ✅ Audio ✅ Text ✅ Agent ✅ |
| **新工具入口** | Top 100 实时排名 |
| **反爬保护** | ❌ **高（Cloudflare 强制人机验证）** |
| **Jina Reader** | ❌ **不可行**（被 Cloudflare 拦截）|
| **提交价格（参考）** | $47 标准 / $199-229 高级 |
| **DR 权重** | ~69 |

**致命问题：** 实测直接访问被 Cloudflare 拦截。自动化抓取方案（Jina Reader / web_fetch / curl）均无法绕过。服务器 2H4G Ubuntu 无法运行 Playwright headless 浏览器。

**备选方案：** `web_search: site:topai.tools new AI tool` 可间接获取 Google 索引页面，但延迟 1-3 天，信息有限。

**结论：❌ 不建议接入。Cloudflare 反爬使自动化不可行，且 Toolify.ai 已覆盖同等内容。**

---

### 2.3 SaaSHub

| 维度 | 详情 |
|------|------|
| **平台类型** | 通用 SaaS 对比平台 |
| **收录规模** | 217,000+ SaaS（AI 子库 46,000+）|
| **月访问量** | ~500K+ |
| **DR 权重** | ~76-77 |
| **更新频率** | 每日（编辑精选 + 社区验证）|
| **品类覆盖** | AI 品类 ✅（但偏 SaaS 替代品对比，覆盖太广）|
| **新工具入口** | Recently Verified / Trending / Experts |
| **Sitemap / RSS** | ❌ 无公开 sitemap / 无 RSS |
| **API** | 有限 API（alternatives 端点）|
| **反爬保护** | 🟡 中（标准网页，无强反爬）|
| **Jina Reader** | 🟡 **可行**（无 Cloudflare）|
| **信噪比** | 🟡 中（AI 只是子集，SaaS 通用类噪音多）|
| **与现有源重叠度** | 中（与 PH 的 SaaS 类产品重叠较多）|
| **jxp.com 匹配度** | 🟡 一般（覆盖太广，AI 生成工具是小子集）|

**结论：🟡 技术可行但信号源价值一般。AI 只是其 217,000+ SaaS 的子集，信噪比不如专门 AI 目录站。建议首期不接入，观察 Toolify 效果后再决定。**

---

## 三、扩展调研的平台

### 3.1 There's An AI For That (TAAFT)

| 维度 | 详情 |
|------|------|
| **平台类型** | 全球最大 AI 工具目录（自称 #1）|
| **收录规模** | 47,000+ 工具，11,000+ 任务分类 |
| **月访问量** | 极高（声称 80M+ 用户）|
| **DR 权重** | ~75-80 |
| **更新频率** | 极高（每小时多次更新，估计每日 10-25 个新工具）|
| **品类覆盖** | Video ✅ Image ✅ Audio ✅ Text ✅ Agent ✅ |
| **新工具入口** | 首页 "Latest" 标签（按时间倒序）|
| **Sitemap** | 有，但 Cloudflare 保护 |
| **RSS** | ❌ 无 |
| **反爬保护** | ❌ **很高（Cloudflare Turnstile + 严格 robots.txt，禁止商业爬虫）** |
| **Jina Reader** | ❌ **不可行**（触发人机验证）|
| **信噪比** | 高（纯 AI 工具）|
| **与现有源重叠度** | 低-中 |

**核心矛盾：** TAAFT 是内容最丰富的 AI 目录站（47,000+ 工具），但反爬保护也最严格。

**降级方案可行：** `web_search: site:theresanaiforthat.com new AI video tool` — 利用 Google 索引间接获取。延迟约 1-3 天，但仍有独特价值（TAAFT 收录的长尾工具其他站可能没有）。

**结论：🟡 直接抓取不可行，但可通过 web_search 降级方式零成本纳入任务。**

---

### 3.2 Futurepedia

| 维度 | 详情 |
|------|------|
| **平台类型** | 精选 AI 工具目录 |
| **收录规模** | ~2,600-4,000 工具（编辑精选制）|
| **DR 权重** | ~70 |
| **更新频率** | 每日更新（首页 "Recently Added" 模块）|
| **品类覆盖** | Video(201) ✅ Image(319) ✅ Audio(160) ✅ Text(320) ✅ Agent ✅ |
| **新工具入口** | `/ai-tools?sort=newest`（最新排序）+ 首页 "Recently Added" |
| **Sitemap** | ✅ `sitemap_tools.xml`（1,341 工具 URL + lastmod 日期）|
| **反爬保护** | ⭐ **低**（无 Cloudflare）|
| **Jina Reader** | ⭐ **优秀**（`r.jina.ai` 实测成功返回干净 markdown）|
| **信噪比** | ⭐ **>95%**（编辑精选，质量高于海量收录的 TAAFT）|
| **与现有源重叠度** | 低 |

**独特优势：**
- **编辑精选制** = 信噪比极高，TAAFT 收录几万个工具（含大量低质 wrapper），Futurepedia 精选几千个高质量工具
- Jina Reader 实测可用，抓取 `/ai-tools?sort=newest` 返回干净的最新工具列表
- Next.js 架构，页面 `__NEXT_DATA__` JSON 包含结构化数据

**结论：⭐ 推荐接入。与 Toolify 互补 — Toolify 覆盖广度，Futurepedia 保证质量。**

---

### 3.3 FutureTools

| 维度 | 详情 |
|------|------|
| **平台类型** | 精选策展 AI 工具目录 |
| **DR 权重** | ~65 |
| **更新频率** | 偏低（强调 trending / novel）|
| **规模** | 较小 |
| **反爬保护** | 未深度测试 |

**结论：🟡 规模和更新频率不如 Toolify/Futurepedia，暂不接入，列为后续候选。**

---

### 3.4 AlternativeTo

| 维度 | 详情 |
|------|------|
| **平台类型** | 通用软件替代品平台 |
| **DR 权重** | ~80（极高）|
| **AI 相关性** | 🟡 AI 只是子集，覆盖所有软件品类 |
| **信噪比** | 低（非 AI 聚焦）|

**结论：❌ 偏「替代品搜索」定位，AI 信号源价值有限。不适合关键词发现。**

---

## 四、全景对比总结

| 平台 | 规模 | 反爬 | Jina可行 | 信噪比 | jxp匹配 | 信号源评级 |
|------|:----:|:----:|:--------:|:------:|:------:|:---------:|
| **Toolify.ai** | 28,500+ | ⭐低 | ✅ 是 | 高 | ⭐最高 | ⭐ **主力接入** |
| **Futurepedia** | ~2,600+ | ⭐低 | ✅ 是 | ⭐极高 | 高 | ⭐ **辅助接入** |
| **TAAFT** | 47,000+ | ❌高 | ❌ 否 | 高 | 高 | 🟡 **降级接入(web_search)** |
| **SaaSHub** | 46,000+ AI | 🟡中 | ✅ 是 | 中 | 中 | 🟡 **二期观察** |
| **topai.tools** | 未知 | ❌高 | ❌ 否 | 高 | 高 | ❌ **不接入** |
| **FutureTools** | 较小 | 未测 | 未测 | 高 | 中 | 🟡 **二期观察** |
| **AlternativeTo** | 泛 | 未测 | 未测 | 低 | 低 | ❌ **不适合** |

---

## 五、结论

推荐新增 1 个 cron 任务 `seo-aitool-directory`，整合 3 个可行源：
1. **Toolify.ai**（Jina Reader 主力抓取）
2. **Futurepedia**（Jina Reader 辅助抓取）
3. **TAAFT**（web_search 降级抓取）

预期日均产出 2-5 个 product 类新词，单词成本 ~$0.07-0.15（可能是全源最低），空跑率 <10%。

详见配套文档《迭代方案-AI工具目录站信号源扩展》。
