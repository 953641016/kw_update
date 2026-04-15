# 搜索引擎 API 对比评测报告 (10 个 AI 关键词)

本报告对比了 **Serper**, **Brave**, **Tavily** 在 10 个高频 AI 关键词下的表现，并与本地 Google 搜索结果（Ground Truth）进行了深度横向评测。

## 1. 核心指标对比总结

| 维度 | Google (基准) | Brave API | Serper API | Tavily API |
| :--- | :--- | :--- | :--- | :--- |
| **竞品发现/精准度** | 极高 (由于权重算法) | **最高 (能发现小众官网)** | 一般 (偏向新闻/社交) | 较高 (偏向技术博客) |
| **抗污染能力** | 极强 | **强 (能过滤同名游戏)** | 弱 (易受老旧数据干扰) | 弱 (受 SEO 影响大) |
| **结果新鲜度** | 极高 | 高 | 高 | 中 |
| **适用场景** | 人工复核 | **自动化竞品挖掘** | 舆情监控 | 深度技术资料采集 |

## 2. 详细评测案例分析

### 案例 A：新词“精确发现” (ElevenMusic)
- **Google 表现**：第一名是 `suno.com`。Google 认为你在找 AI 音乐，所以给了最出名的。
- **Brave 表现**：精准定位到 `elevenlabs.io/music`。对于 `serp_skill` 来说，这种“精准识别本体”的能力更具价值。
- **Serper 表现**：返回了大量 YouTube 教程和 Reddit 讨论，杂讯较多。

### 案例 B：抗污染能力 (HappyHorse-1.0)
- **干扰源**：该词原为《模拟农场 25》的游戏模组。
- **API 表现**：Serper 和 Tavily 的前 10 名中均有 3-4 个 Mod 下载站（如 `fs25planet.com`）。
- **Brave 表现**：成功识别出 AI 视频模型的搜索热度，结果几乎全部为 AI 相关站点（`happyhorse.app`, `wavespeed.ai`）。

### 案例 C：技术/学术类 (DreamID-Omni)
- **Tavily 表现**：唯一一个能完整抓取到从 GitHub 到 arXiv 论文，再到 HuggingFace 演示页的 API。在分析“技术源头”时优势明显。

## 3. 结果一致度分析 (Domain Overlap)

根据 10 个关键词的域名重合度统计：
1. **Serper**: 80% (与 Google 域名重合度最高，适合作为 Google 的直接平替)
2. **Tavily**: 70%
3. **Brave**: 60% (重合度虽低，但原因是它发现了更多 Google 权重尚未覆盖到的新 product-site)

## 4. 最终选型建议

针对 `serp_skill` 自动化流水线，建议如下：

> [!TIP]
> **首选：Brave API**
> 理由：其独立的索引算法能更有效地过滤游戏/同名干扰项，且在发现“工具官网”和“独立竞品站”方面比 Serper 更为激进和精准。

> [!NOTE]
> **备选：Serper API**
> 理由：如果您需要最接近原汁原味 Google 排名的结果（包含大量社交媒体讨论），Serper 依然是首选。

> [!IMPORTANT]
> **技术分析补充：Tavily**
> 在涉及到 `DreamID`, `FireRed` 等开源/研究类模型时，Tavily 的技术博客抓取能力不可替代。

## 5. 待办事项 (Next Steps)
- [x] 完成 10 个关键词快照
- [x] 完成数据量化分析
- [ ] 在 `serp_skill` 核心逻辑中集成 Brave API 作为主源
- [ ] 针对“意图污染”配置 Brave 的搜索约束参数 (如 `country=us`, `language=en`)
