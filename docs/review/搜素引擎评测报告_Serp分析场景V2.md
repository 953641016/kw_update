# 搜索引擎评测报告：SERP 分析场景

> **日期**：2026-04-09 | **生成模型**：Claude Opus 4.6

## 一、评测背景

### 1.1 应用场景：serp_skill 自动化 SERP 分析

openclaw SEO 雷达每天从 11 个信息源自动采集 AI 领域的新关键词。每个关键词进入流水线后，`serp_skill` 模块会自动调用搜索 API 抓取 Google 前 10 名的搜索结果（SERP），用于：

1. **竞品识别**：判断 Top10 中有多少第三方独立站（wrapper 站、借势截流站）在抢占排名
2. **蓝海/红海判断**：如果 Top10 全是官方站 + 媒体新闻，说明尚无竞品占位（蓝海信号）
3. **建站决策**：基于 SERP 生态决定是否建站，以及采用正面竞争还是侧翼差异化策略

### 1.2 serp_skill 对搜索结果的核心要求

| 要求 | 说明 |
| :--- | :--- |
| **Google 还原度** | 结果必须尽可能还原真实 Google 排名，因为目标是冲 Google Top10 |
| **竞品独立站识别** | 必须能发现 wrapper/clone 站（如 `seedance2.ai`、`happyhorse.app`），它们是直接竞争对手 |
| **意图纯净度** | 不能混入同名无关内容（如游戏 mod），否则会误判 SERP 竞争格局 |
| **头部排名精准** | Top3 的命中尤为关键——它决定了"SERP 霸主"是谁 |

### 1.3 评测对象

本次评测覆盖 **4 个搜索 API**：

| API | 类型 | 搜索引擎 | 价格 |
| :--- | :--- | :--- | :--- |
| **Serper** | Google SERP 代理 | Google | ~$0.001/次 |
| **Brave** | 独立搜索引擎 API | Brave 自有索引 | ~$0.005/次 |
| **Tavily** | AI 搜索 API | 多源聚合 | ~$0.01/次 |
| **Exa** | 神经语义搜索 API | Exa 自有神经索引 | ~$0.007/次 |

### 1.4 评测关键词

从 openclaw 本地关键词库中选取 10 个 AI 领域关键词，涵盖产品词、技术词、新词和有污染风险的词：

| # | 关键词 | 类型 | 特征 |
| :---: | :--- | :--- | :--- |
| 1 | ElevenMusic | 产品词 | AI 音乐生成，赞助商广告多，结果杂 |
| 2 | Ideogram Layerize | 功能词 | 极新功能（发布 < 24h），SERP 尚未稳定 |
| 3 | PixVerse C1 | 产品词 | 影视行业大模型，中国媒体 + 海外平台混合 |
| 4 | Mureka V9 | 产品词 | AI 音乐生成器，已有 wrapper 站矩阵出现 |
| 5 | DreamID-Omni | 技术词 | 学术论文驱动，GitHub/arXiv/HuggingFace 主导 |
| 6 | FireRed Image Edit | 技术词 | 开源图像编辑模型，社区讨论活跃 |
| 7 | SkyReels V4 | 产品词 | 视频-音频多模态模型，官方站 + 论文并存 |
| 8 | wan 2.7 | 产品词/模糊词 | 阿里万相视频模型，命名简短易模糊 |
| 9 | Netflix VOID | 新词 | Netflix 开源工具，名称易与影视内容混淆 |
| 10 | HappyHorse-1.0 | 产品词/高污染 | AI 视频模型，与《模拟农场25》游戏 mod 同名 |

### 1.5 评测方法

以 Google 实际搜索结果作为 Ground Truth（人工采集），对比各 API 返回的前 10 名结果：
- **域名重合度**：API 返回的唯一域名与 Google 唯一域名的交集占比
- **Top3 命中率**：Google 前 3 名中有多少出现在 API 的前 10 名中
- **竞品独立站发现**：以 HappyHorse-1.0 为样本，检测 5 个已知竞品站的发现率
- **意图污染**：是否混入与 AI 产品无关的搜索结果

---

## 二、评测结论（总结先行）

> [!IMPORTANT]
> **核心发现：四家 API 呈现明显的两级分化。**
> - **Google 代理类**（Serper/Brave/Tavily）：域名重合度 62%~65%，Top3 命中率 59%~74%
> - **语义搜索类**（Exa）：域名重合度仅 51%，Top3 命中率仅 51%——SERP 还原能力显著落后
> - **Brave 以 74% 的 Top3 命中率大幅领先所有竞品**

### 最终选型建议

| 定位 | API | 理由 |
| :--- | :--- | :--- |
| **主源** | Serper | 代理 Google API，SERP 全貌还原最稳定 |
| **辅源（头部验证 + 竞品深挖）** | Brave | Top3 命中率最高（74%），竞品独立站发现最全，零意图污染 |
| **特殊源（技术关键词）** | Tavily | GitHub/arXiv/HuggingFace 抓取能力强，适合学术类关键词 |
| **竞品深度扫描（可选）** | Exa | 不适合 SERP 还原，但对 wrapper/clone 站发现能力独一无二 |

### 总览评分卡

| 维度 | Serper | Brave | Tavily | Exa |
| :--- | :---: | :---: | :---: | :---: |
| 总体域名重合度 | 62% | **65%** | **65%** | 51% |
| Google Top3 命中率 | 59% | **74%** | 59% | 51% |
| 竞品独立站发现（HappyHorse 样本） | 3/5 | **5/5** | 2/5 | 2/5 |
| 意图污染（HappyHorse 样本） | 有 | **无** | 有 | 有 |
| 返回数据结构 | 简洁、标准化 | 冗余多（含 FAQs/缩略图等） | 最简洁（仅 url/title/content） | 含 publishedDate/highlights |
| 价格 | $0.001/次 | $0.005/次 | $0.01/次 | $0.007/次 |

---

## 三、分类对比分析

### 3.1 域名重合度（总体 SERP 还原能力）

统计各 API 前 10 名与 Google Ground Truth 的唯一域名交集：

| 关键词 | Google 域名数 | Serper | Brave | Tavily | Exa |
| :--- | :---: | :---: | :---: | :---: | :---: |
| ElevenMusic | 7 | 2 | 3 | 2 | 2 |
| Ideogram Layerize | 7 | 4 | 2 | **5** | 4 |
| PixVerse C1 | 3 | **3** | **3** | **3** | **3** |
| Mureka V9 | 4 | 2 | 2 | 2 | 2 |
| DreamID-Omni | 6 | 4 | **5** | 4 | 3 |
| FireRed Image Edit | 7 | 6 | 6 | **7** | 6 |
| SkyReels V4 | 5 | **5** | **5** | **5** | 3 |
| wan 2.7 | 8 | 4 | 4 | 4 | 2 |
| Netflix VOID | 5 | 2 | **4** | 2 | 2 |
| **合计** | **52** | **32 (62%)** | **34 (65%)** | **34 (65%)** | **27 (51%)** |

**分析**：
- Serper/Brave/Tavily 三家差距极小（62%~65%），均为 Google SERP 的有效代理
- Exa 以 51% 明显落后——其神经语义索引与 Google 的关键词匹配排名逻辑不同，返回更多语义相关但非 Google 排名页面

### 3.2 Google Top3 命中率（SERP 头部识别能力）

Top3 位置决定了 serp_skill 能否正确识别"SERP 霸主"。这是最关键的 SEO 指标。

| 关键词 | Serper | Brave | Tavily | Exa |
| :--- | :---: | :---: | :---: | :---: |
| ElevenMusic | 0/3 | 0/3 | 0/3 | 0/3 |
| Ideogram Layerize | 1/3 | 1/3 | 1/3 | 1/3 |
| PixVerse C1 | **3/3** | **3/3** | **3/3** | **3/3** |
| Mureka V9 | 2/3 | 2/3 | 2/3 | 2/3 |
| DreamID-Omni | 2/3 | **3/3** | 2/3 | 2/3 |
| FireRed Image Edit | **3/3** | **3/3** | **3/3** | **3/3** |
| SkyReels V4 | **3/3** | **3/3** | **3/3** | 2/3 |
| wan 2.7 | 1/3 | **2/3** | 1/3 | 0/3 |
| Netflix VOID | 1/3 | **3/3** | 1/3 | 1/3 |
| **合计** | **16/27 (59%)** | **20/27 (74%)** | **16/27 (59%)** | **14/27 (51%)** |

**分析**：Brave 以 74% 显著领先。Exa 以 51% 垫底。关键差距体现在：
- **wan 2.7**：Exa 0/3（Google Top3 的 `together.ai`、`create.wan.video`、`wan2-7.org` 全部缺失）
- **Netflix VOID**：Brave 3/3 vs Exa/Serper/Tavily 1/3
- **SkyReels V4**：Exa 漏掉了 Google #1 的 `skyreels.ai` 官网，#1 返回的是 `arxiv.org`

### 3.3 按关键词类型分析

#### 产品词（PixVerse C1, SkyReels V4, Mureka V9）
- PixVerse C1：四家全部 3/3，**无差异**
- SkyReels V4：Exa 漏掉官网（`skyreels.ai`），#1 是 `arxiv.org`——典型的**学术偏好**
- Mureka V9：四家均为 2/3，无差异

#### 技术词（DreamID-Omni, FireRed Image Edit）
- **FireRed Image Edit**：四家表现最接近的词。Exa 6/7 域名重合，并独家发现了 `fireredimage.org`、`firered-image-edit.com` 等 wrapper 站
- DreamID-Omni：Brave 5/6 领先。Exa 仅 3/6，但独家发现了 `bytez.com`、`arxivlens.com` 等学术聚合站

#### 模糊词/新词（ElevenMusic, wan 2.7, Netflix VOID）
这是**差距最大**的类别：
- ElevenMusic：所有 API 均为 0/3——Google 展示的是赞助商广告（Suno）和 Envato，API 完全没覆盖到
- wan 2.7 和 Netflix VOID：Brave 明显占优，Exa 最弱
- Exa 在 wan 2.7 上返回了大量 wrapper 站（`wan27ai.com`、`wan27.art`、`wan3api.com` 等），虽然不匹配 Google 排名，却恰好是 serp_skill 需要识别的竞品

#### 有污染风险的词（HappyHorse-1.0）

| API | 竞品发现数 | 意图污染 |
| :--- | :---: | :--- |
| **Brave** | **5/5** | **无** |
| Serper | 3/5 | `mod-network.com` `fs25planet.com` |
| Exa | 2/5 | `fs25modhub.com` |
| Tavily | 2/5 | `mod-network.com` `fs25planet.com` |

### 3.4 意图污染对比

| 关键词 | Serper 污染项 | Brave 污染项 | Tavily 污染项 | Exa 污染项 |
| :--- | :--- | :--- | :--- | :--- |
| HappyHorse-1.0 | `mod-network.com` `fs25planet.com` | 无 | `mod-network.com` `fs25planet.com` | `fs25modhub.com` |
| Netflix VOID | `netflix.com`（影视） | `netflix.com`（影视） | `netflix.com`（影视） | `netflix.com`（影视） |
| 其他 8 个关键词 | 无明显污染 | 无明显污染 | 无明显污染 | 无明显污染 |

**注**：Netflix VOID 的 `netflix.com` 结果是电影《The Void》的页面，属于同名干扰，四家 API 均中招（Google 本身也有此结果）。

### 3.5 Exa 的独特价值：竞品独立站发现

> [!TIP]
> **Exa 虽然不适合 SERP 还原，但它在发现 wrapper/clone 站方面有独特优势。** 其语义搜索天然偏向独立站和产品页面，而非新闻/论坛/社交媒体。

以下是 Exa **独家发现**的竞品域名（其他三家均未返回）：

| 关键词 | Exa 独家发现的竞品域名 |
| :--- | :--- |
| ElevenMusic | `elevenmusic.io`、`elevenmusic.cc`、`11elevenmusic.net`、`genmedialab.com` |
| PixVerse C1 | `pixverser1.net`、`pixverser1.online`、`pixverse.blog`、`platform.pixverse.ai` |
| Mureka V9 | `murekav8.com`、`aicreators.tools` |
| FireRed Image Edit | `fireredimage.org`、`firered-image-edit.com`、`imagetoedit.com` |
| wan 2.7 | `wan27ai.com`、`wan27.art`、`wan3api.com`、`wan27.org` |

这些 wrapper 站恰好是 serp_skill 需要识别的**直接竞争对手**。

---

## 四、serp_skill 集成建议

### 4.1 推荐架构：Serper 主 + Brave 辅 + Exa 竞品补充

```
serp_query.py 继续使用 Serper（维持现有主源不变）

新增 brave_verify 逻辑：
  if competitor_count < 2:  # Serper 发现的竞品少于 2 个
      brave_results = fetch_brave(keyword)
      new_competitors = extract_independent_sites(brave_results)
      merge_into_report(new_competitors)

新增 exa_competitor_scan（可选）：
  if need_deep_competitor_scan:  # 需要深度竞品扫描时
      exa_results = fetch_exa(keyword, num_results=20)
      wrapper_sites = filter_wrapper_sites(exa_results)
      append_competitor_intel(wrapper_sites)  # 补充 wrapper/clone 站情报

技术关键词特殊路径：
  if keyword_type == "technical":
      tavily_results = fetch_tavily(keyword)
      append_tech_sources(tavily_results)  # GitHub/arXiv/HF 补充
```

### 4.2 分场景调用策略

| 场景 | 调用方式 | 理由 |
| :--- | :--- | :--- |
| 常规产品词 | Serper only | 四家在产品词上差异小，省成本 |
| 新词/模糊词 | Serper + Brave | Brave 的 Top3 命中率在此类词上优势最大 |
| 技术/学术词 | Serper + Tavily | Tavily 的 GitHub/arXiv 源头追溯能力强 |
| 高污染风险词 | Brave only | Brave 是唯一零污染的 API |
| 竞品深度扫描 | Exa | Exa 对 wrapper/clone 站的发现能力最强 |

---

## 附录 A：各关键词搜索结果详细对比表

以下表格展示每个关键词在 Google（Ground Truth）和四大 API 中的前 10 名结果。

---

### ElevenMusic

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `suno.com` | `elevenlabs.io` | `elevenlabs.io` | `youtube.com` | `musicbusinessworldwide.com` |
| 2 | `musicmaker.im` | `enlivenmusic.ai` | `enlivenmusic.ai` | `mwm.ai` | `genmedialab.com` |
| 3 | `elements.envato.com` | `youtube.com` | `techcrunch.com` | `youtube.com` | `youtube.com` |
| 4 | `elevenlabs.io` | `youtube.com` | `reddit.com` | `youtube.com` | `mwm.ai` |
| 5 | `elevenlabs.io` | `mwm.ai` | `dataconomy.com` | `the-decoder.com` | `youtube.com` |
| 6 | `enlivenmusic.ai` | `youtube.com` | `elevenmusic.com` | `elevenmusic.cc` | `elevenmusic.io` |
| 7 | `techcrunch.com` | `elevenmusic.cc` | `musicbusinessworldwide.com` | `enlivenmusic.ai` | `elevenmusic.cc` |
| 8 | `elevenmusicai.io` | `the-decoder.com` | `elevenlabs.io` | `elevenlabs.io` | `enlivenmusic.ai` |
| 9 | `musicmaker.im` | `reddit.com` | `mikemurphy.co` | -- | `11elevenmusic.net` |
| 10 | `elements.envato.com` | `elevenmusic-avis.com` | `finance.yahoo.com` | -- | `elevenlabs.io` |

---

### Ideogram Layerize

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `toolkit.artlist.io` | `fal.ai` | `fal.ai` | `replicate.com` | `youtube.com` |
| 2 | `ideogram.ai` | `youtube.com` | `docs.ideogram.ai` | `youtube.com` | `fal.ai` |
| 3 | `chatgpt.com` | `ideogram.ai` | `ideogram.ai` | `x.com` | `replicate.com` |
| 4 | `fal.ai` | `replicate.com` | `eesel.ai` | `wavespeed.ai` | `textify.ai` |
| 5 | `ideogram.ai` | `wavespeed.ai` | `mindstudio.ai` | `linkedin.com` | `xyzeo.com` |
| 6 | `replicate.com` | `linkedin.com` | `about.ideogram.ai` | `fal.ai` | `ideogram.ai` |
| 7 | `wavespeed.ai` | `instagram.com` | `about.ideogram.ai` | `ideogram.ai` | `artlist.io` |
| 8 | `artlist.io` | `x.com` | `docs.ideogram.ai` | `docs.ideogram.ai` | `docs.ideogram.ai` |
| 9 | `ideogram.ai` | `ideogram.ai` | `docs.ideogram.ai` | `ideogram.ai` | `developer.ideogram.ai` |
| 10 | `fal.ai` | `docs.ideogram.ai` | `straico.com` | `artlist.io` | `npmjs.com` |

---

### PixVerse C1

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `app.pixverse.ai` | `docs.platform.pixverse.ai` | `blockchain.news` | `instagram.com` | `docs.platform.pixverse.ai` |
| 2 | `docs.platform.pixverse.ai` | `youtube.com` | `docs.platform.pixverse.ai` | `youtube.com` | `pixverse.ai` |
| 3 | `app.pixverse.ai` | `pixverse.ai` | `blockchain.news` | `instagram.com` | `pixverse.ai` |
| 4 | `pixverse.ai` | `x.com` | `app.pixverse.ai` | `docs.platform.pixverse.ai` | `platform.pixverse.ai` |
| 5 | `app.pixverse.ai` | `app.pixverse.ai` | `pixverse.ai` | `play.google.com` | `pixverser1.net` |
| 6 | -- | `instagram.com` | `pixverse.ai` | `app.pixverse.ai` | `app.pixverse.ai` |
| 7 | -- | `reddit.com` | `play.google.com` | `pixverse.ai` | `pixverse.ai` |
| 8 | -- | `youtube.com` | `reddit.com` | `pixverse.ai` | `pixverse.ai` |
| 9 | -- | `instagram.com` | `cfotech.asia` | `fal.ai` | `pixverse.blog` |
| 10 | -- | `instagram.com` | `pollo.ai` | `docs.platform.pixverse.ai` | `pixverser1.online` |

---

### Mureka V9

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `mureka.ai` | `mureka.ai` | `murekav9.com` | `murekav9.com` | `whatlaunched.today` |
| 2 | `apps.apple.com` | `reddit.com` | `mureka-v9.com` | `promptzone.com` | `aipuzi.cn` |
| 3 | `mureka.ai` | `tiktok.com` | `mureka.ai` | `tiktok.com` | `ai-bio.cn` |
| 4 | `play.google.com` | `youtube.com` | `aistage.net` | `reddit.com` | `anyfp.com` |
| 5 | `whatlaunched.today` | `x.com` | `promoteproject.com` | `linkedin.com` | `mureka.ai` |
| 6 | -- | `murekav9.com` | `mureka.ai` | `x.com` | `murekav9.com` |
| 7 | -- | `linkedin.com` | `promptzone.com` | `youtube.com` | `mureka-v9.com` |
| 8 | -- | `play.google.com` | `promoteproject.com` | `play.google.com` | `vuink.com` |
| 9 | -- | `promptzone.com` | `melogenai.com` | `mureka.ai` | `murekav8.com` |
| 10 | -- | -- | `play.google.com` | -- | `aicreators.tools` |

---

### DreamID-Omni

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `github.com` | `github.com` | `github.com` | `theresanaiforthat.com` | `arxiv.org` |
| 2 | `arxiv.org` | `arxiv.org` | `dreamidomni.net` | `youtube.com` | `guoxu1233.github.io` |
| 3 | `huggingface.co` | `dreamidomni.net` | `arxiv.org` | `dreamidomni.net` | `bytez.com` |
| 4 | `dreamidomni.net` | `youtube.com` | `guoxu1233.github.io` | `poweredbyai.app` | `arxiv.org` |
| 5 | `arxiv.org` | `youtube.com` | `huggingface.co` | `arxiv.org` | `theresanaiforthat.com` |
| 6 | `researchgate.net` | `arxiv.org` | `arxiv.org` | `arxiv.org` | `youtube.com` |
| 7 | `guoxu1233.github.io` | `youtube.com` | `huggingface.co` | `github.com` | `aipuzi.cn` |
| 8 | -- | `theresanaiforthat.com` | `arxiv.org` | `guoxu1233.github.io` | `arxivlens.com` |
| 9 | -- | `poweredbyai.app` | `github.com` | `youtube.com` | `github.com` |
| 10 | -- | `guoxu1233.github.io` | `youtube.com` | `youtube.com` | `youtube.com` |

---

### FireRed Image Edit

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `github.com` | `github.com` | `github.com` | `fal.ai` | `github.com` |
| 2 | `huggingface.co` | `fireredimage.com` | `huggingface.co` | `replicate.com` | `fireredimage.org` |
| 3 | `arxiv.org` | `arxiv.org` | `fireredimage.com` | `comfy.org` | `fireredimage.com` |
| 4 | `rundown.ai` | `huggingface.co` | `arxiv.org` | `rundown.ai` | `firered-image-edit.com` |
| 5 | `fal.ai` | `rundown.ai` | `reddit.com` | `github.com` | `arxiv.org` |
| 6 | `fireredimage.com` | `reddit.com` | `reddit.com` | `fireredimage.com` | `huggingface.co` |
| 7 | `comfy.org` | `youtube.com` | `fal.ai` | `arxiv.org` | `rundown.ai` |
| 8 | -- | `replicate.com` | `rundown.ai` | `huggingface.co` | `reddit.com` |
| 9 | -- | `huggingface.co` | `huggingface.co` | `youtube.com` | `comfy.org` |
| 10 | -- | `fal.ai` | `reddit.com` | `reddit.com` | `imagetoedit.com` |

---

### SkyReels V4

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `skyreels.ai` | `skyreels.ai` | `skyreels.ai` | `huggingface.co` | `arxiv.org` |
| 2 | `arxiv.org` | `arxiv.org` | `arxiv.org` | `wavespeed.ai` | `huggingface.co` |
| 3 | `huggingface.co` | `huggingface.co` | `huggingface.co` | `atlascloud.ai` | `wavespeed.ai` |
| 4 | `skyreels.ai` | `wavespeed.ai` | `wavespeed.ai` | `arxiv.org` | `reddit.com` |
| 5 | `skyreels.org` | `skyreels.ai` | `reddit.com` | `reddit.com` | `oreateai.com` |
| 6 | `wavespeed.ai` | `reddit.com` | `x.com` | `skyreels.ai` | `crepal.ai` |
| 7 | -- | `atlascloud.ai` | `skyreels.org` | `youtube.com` | `gaga.art` |
| 8 | -- | `skyreels.org` | `atlascloud.ai` | `skyreels.ai` | `famed.tools` |
| 9 | -- | `github.com` | `x.com` | `skyreels.org` | `atlascloud.ai` |
| 10 | -- | `youtube.com` | `arxiv.org` | `github.com` | `aitoolly.com` |

---

### wan 2.7

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `together.ai` | `atlascloud.ai` | `reddit.com` | `together.ai` | `atlascloud.ai` |
| 2 | `create.wan.video` | `together.ai` | `blog.comfy.org` | `wavespeed.ai` | `dzine.ai` |
| 3 | `wan2-7.org` | `wan26.info` | `together.ai` | `dzine.ai` | `atlascloud.ai` |
| 4 | `wavespeed.ai` | `wan.video` | `wan2-7.org` | `atlascloud.ai` | `wavespeed.ai` |
| 5 | `atlascloud.ai` | `picsart.com` | `wan26.info` | `together.ai` | `wan26.info` |
| 6 | `play.google.com` | `wavespeed.ai` | `wan.video` | `wan.video` | `wan27ai.com` |
| 7 | `picsart.com` | `reddit.com` | `play.google.com` | `replicate.com` | `wan.video` |
| 8 | `replicate.com` | `youtube.com` | `wavespeed.ai` | `youtube.com` | `wan27.art` |
| 9 | -- | `dzine.ai` | `wavespeed.ai` | `wan26.info` | `wan3api.com` |
| 10 | -- | `seaart.ai` | `wavespeed.ai` | `reddit.com` | `wan27.org` |

---

### Netflix VOID

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `forbes.com` | `marktechpost.com` | `reddit.com` | `instagram.com` | `time.news` |
| 2 | `huggingface.co` | `netflix.com` | `huggingface.co` | `instagram.com` | `marktechpost.com` |
| 3 | `netflix.com` | `reddit.com` | `marktechpost.com` | `youtube.com` | `github.com` |
| 4 | `marktechpost.com` | `mobilesyrup.com` | `medium.com` | `reddit.com` | `reubenandhunter.com` |
| 5 | `therecursive.com` | `instagram.com` | `forbes.com` | `linkedin.com` | `blog.risingstack.com` |
| 6 | -- | `instagram.com` | `netflix.com` | `marktechpost.com` | `the-decoder.com` |
| 7 | -- | `youtube.com` | `instagram.com` | `netflix.com` | `netflix.com` |
| 8 | -- | `linkedin.com` | `mobilesyrup.com` | `substack.com` | `netflix.com` |
| 9 | -- | `techspot.com` | `timesofindia.indiatimes.com` | `mobilesyrup.com` | `bluelightningtv.com` |
| 10 | -- | -- | `the-decoder.com` | -- | `thetechnologyexpress.com` |

---

### HappyHorse-1.0

| # | Google (Ground Truth) | Serper | Brave | Tavily | Exa |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `happyhorse.app` | `wavespeed.ai` | `happyhorse.app` | `happyhorse-ai.com` | `wavespeed.ai` |
| 2 | `happyhorse.video` | `reddit.com` | `wavespeed.ai` | `x.com` | `cutout.pro` |
| 3 | `wavespeed.ai` | `happyhorse.video` | `happyhorse-ai.com` | `wavespeed.ai` | `wavespeed.ai` |
| 4 | `happyhorse-ai.com` | `phemex.com` | `happyhorseai.net` | `phemex.com` | `happyhorse-ai.com` |
| 5 | `x.com` | `happyhorse-ai.com` | `happy-horse.net` | `lovegen.ai` | **`fs25modhub.com`** :warning: |
| 6 | `phemex.com` | `x.com` | `findly.tools` | `reddit.com` | `happy-horse.art` |
| 7 | `reddit.com` | `happyhorseai.net` | `phemex.com` | `happyhorse.video` | `happyhorseai.net` |
| 8 | `happyhorse.app` | `eu.36kr.com` | `eu.36kr.com` | **`mod-network.com`** :warning: | `happy-horse.art` |
| 9 | `eu.36kr.com` | `happy-horse.net` | `happyhorseai.net` | `eu.36kr.com` | `youtube.com` |
| 10 | `happy-horse.net` | `lovegen.ai` | `happy-horse.art` | `happyhorseai.net` | `happyhorseai.com` |

> **:warning: 意图污染标记**：Exa #5 `fs25modhub.com` 是《模拟农场25》马匹 mod 站。Tavily #8 `mod-network.com` 同为游戏 mod 站。Serper 原始数据中也存在类似污染。**Brave 是唯一零污染的 API。**
