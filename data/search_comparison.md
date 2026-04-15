# 搜索引擎 API 对比分析: `HappyHorse-1.0` 

数据来源包含：**本地 Google 抓取**、**Serper (基于 Google API)**、**Brave API**、**Tavily API**。所有的结果原始数据均已快照至 `api_snapshots.json`。

---

## 🔝 Top 1 - 10 并排比对矩阵表

以下表格提取了前十名的**核心来源域名或标识**，直观对比四个来源的排位倾向：

| 排名 | Local_Google (本地环境直出) | Serper API (纯净代理节点) | Brave Search API | Tavily API (AI 聚合) |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `happyhorse.app` (衍生官网) | `x.com` (@venturetwins) | `happyhorse.app` (衍生官网) | `happyhorse-ai.com` |
| **2** | `happyhorse.video` | `reddit.com/r/aivideos` | `happyhorse-ai.com` | `fs25planet.com` ❌(农游戏) |
| **3** | `wavespeed.ai` (新闻分析) | `happyhorseai.net` | `happyhorseai.net` | `x.com/Elaina...` |
| **4** | `happyhorse-ai.com` | `happyhorse-ai.com` | `findly.tools` (AI导航站) | `x.com/arsh_goyal` |
| **5** | `x.com` (@venturetwins) | `happyhorse.video` | `wavespeed.ai` (新闻) | `reddit.com/r/aivideos` |
| **6** | `phemex.com` (新闻) | `x.com/arsh_goyal` | `happy-horse.net` | `happyhorse.video` |
| **7** | `reddit.com` (/r/aivideos) | `mod-network.com` ❌(农游戏) | `happyhorseai.net` (/pricing) | `mod-network.com` ❌(农游戏)|
| **8** | `happyhorse.app` (/Dashboard) | `x.com/imgn_ai` | `happy-horse.art` (新衍生) | `x.com/venturetwins` |
| **9** | `36kr.com` (权威媒体) | `x.com/Elaina...` | `x.com/ArtificialAnlys` | `x.com/imgn_ai` |
| **10**| `happy-horse.net` | `fs25planet.com` ❌(农游戏) | `36kr.com` (权威媒体) | `happyhorseai.net` |

---

## 🎯 深度分析洞察 (Data Insights)

1. **地理环境差异（Local_Google vs Serper）**：
   - 极其出乎意料，**Serper（理应与 Google 完全一致）却出现了巨大偏差**。它不仅把 X(推特) 和 Reddit 推到了最顶端，甚至和 Tavily 一样，被骗到了《模拟农场25 (FS25)》的同名马匹模组。
   - **原因剖析**：您本地 Google 返回的结果高度精准，是因为叠加了**浏览器本地化、个人搜索习惯以及地理偏好**；而 Serper 用的是无痕的海外（如美国）纯净节点。在全网爆发初期，纯净节点的默认权重被各大资讯社媒暂时占据，且因为缺乏前置语境过滤，被旧游戏名称污染了数据。

2. **Brave API 表现抢眼（防污染能力强）**：
   - 在三个第三方 API 中，**Brave 竟是唯一一个没有被“老游戏数据(FS25 mods)”污染的引擎**。它精准地包揽了各大打着 `HappyHorse` 旗号的衍生工具站（`.app`、`.art`、`.net`），甚至囊括了诸如 `findly.tools` 这类的 AI 工具导航站和 `36kr` 新闻源。
   - Brave 对“工具类”产品的嗅觉非常优秀，非常适合用来挖掘“未注册完全的野生竞品站矩阵”。

3. **Tavily 与 Serper 居然“异曲同工”**：
   - 观察表格可发现，Tavily 和 Serper 在 10 个条目中，都有大量社媒内容充斥（X 讨论），且都在第2或第7、第10位踩中了修马游戏模组（`fs25planet` 和 `mod-network`）。这严重说明它们两者在当下的无痕语义联想上容易跑偏，需要极强的附加 Prompt 限定（例如加上 `AI Video model` 作为强制约束词）才能有效调用！
