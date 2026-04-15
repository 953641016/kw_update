# 迭代方案：AI 工具目录站信号源扩展（V4）

**更新时间：2026-04-01**
**版本：V4（终稿，已通过审查）**

> 调研详情见 [调查报告-AI工具目录站信号源扩展](file:///Users/zhangjian/project/keyword/docs/调查报告-AI工具目录站信号源扩展.md)

---

## ⚠️ 同步信息

> [!NOTE]
> **关于 HN 信号源状态**
> 远程 OpenClaw 上的 `seo-hackernews` 已经下线，本地 `jobs.json` 代码状态待同步更新。
> 本方案任务 `seo-aitool-directory` 将直接复用原 HN 的时间槽 (`0 20 * * *`)。

---

## 一、背景与目标

当前 SEO 雷达缺少「目录站」维度的信号。大量中小 AI 工具不走 PH/Reddit，但会去 Toolify、Futurepedia 等目录站提交以获取流量。

**核心问题（V3 解决）：**
1. **数据质量**：从目录站获取的是混合物（产品名、域名、描述）。必须**严格执行“产品名=关键词”**的提取逻辑，过滤掉毫无意义的竞品域名。不要求 LLM 自行根据描述生成需求词（防范质量参差不齐的 SEO 风险）。
2. **工程稳定性**：修复 404 URL (Toolify 改为 `/new`) 和 JS 渲染导致的排序失效 (Futurepedia 改抓首页)。TAAFT 经实测无法被 Jina 抓取，直接降级为 web_search。
3. **消除幻觉**：禁止 LLM 拼接 URL，要求从 Jina 返回的 Markdown 中提取真实工具页链接或就地降级为列表页。
4. **强 Fallback**：增加实质性的 Jina 抓取失败判定（以应对 Cloudflare 等质询页）。

---

## 二、信号源执行策略（V3 最终版）

| 平台 | 获取方式 | 提取策略 | 备注 |
|------|---------|---------|------|
| **Toolify.ai** | `curl https://r.jina.ai/https://www.toolify.ai/new` | 提取 "Just launched" 列表 | 主力源，实测 Jina 可抓，含独立工具链接 |
| **Futurepedia** | `curl https://r.jina.ai/https://www.futurepedia.io/` | 定位 "Recently Added" 模块 | 辅助源，避开排序页的 JS 渲染坑 |
| **TAAFT** | web_search | `site:theresanaiforthat.com ...` | 补充源，实测 Jina 会被拦截(connection reset) |

---

## 三、Cron 任务配置

### 3.1 基础配置

在 `jobs.json` 中新增（或替换 `seo-hackernews`）：

| 参数 | 值 |
|------|---|
| name | `seo-aitool-directory` |
| description | `北京04:00 AI工具目录站新品监控。目标：收集新产品词，过滤域名垃圾。` |
| cron expr | `0 20 * * *`（UTC 20:00 = 北京 04:00，复用 HN 时间槽） |
| 频率 | 每天 1 次 |
| timeoutSeconds | `1800` |
| lightContext | `true` |
| sessionTarget | `isolated` |

### 3.2 完整可执行的 Prompt（payload.message）

```markdown
你是 jxp.com 的 SEO 关键词侦察员。jxp.com 是英文 AI 工具站，覆盖 Video/Image/Audio/Text/Agent 五类 AI 工具。

## 任务：从 AI 工具目录站挖掘新上架的潜质产品词

### 第一步：获取基准日期
```bash
date -u +%Y-%m-%d
```
请记录此 UTC 日期，后续“7天内”的判断均以此为准。

---

### 第二步：提取目录站工具（严格按顺序）

**⚠️ Jina 抓取失败判定（全局规则）：**
在执行 curl 请求后，若返回内容**少于 1000 字节，或内容不包含 'AI' 字样**，视为抓取失败或被反爬。
遇到此情况，立即放弃本信号源，**绝对禁止**基于空内容或报错信息编造任何数据。

#### ① Toolify.ai（主力源，Just launched）
```bash
curl -s "https://r.jina.ai/https://www.toolify.ai/new" --max-time 30
```
**提取规则**：
- 提取 "Just launched" 或类似列表下的工具。
- **只保留页面标注上架/收录时间在 7天内 的工具**。若无明确时间标签，但在 /new 下，默认保留。
- **禁止提取纯域名**（如 `stackie.ai`, `bidhelm.com` 除非它是官方宣传的产品真名），必须提取**产品名**（如 `Kling AI`, `Nano Banana`）。
- **来源链接**：必须从 Markdown 提取指向 `toolify.ai/tool/{slug}` 的独立 URL。**严禁 LLM 拼接 URL**。若提取不到，来源链接填 `https://www.toolify.ai/new`。

#### ② Futurepedia（辅助源，Recently Added）
```bash
curl -s "https://r.jina.ai/https://www.futurepedia.io/" --max-time 30
```
**提取规则**：
- 寻找 "Recently Added" 或最新上架模块。
- 执行与 Toolify 相同的提取和 7天窗口约束。
- **来源链接**：从 Markdown 提取 `futurepedia.io/ai-tools/{slug}`。无法提取则填 `https://www.futurepedia.io/`。

#### ③ TAAFT（补充源，仅 Web Search）
因为 Cloudflare，不走 Jina，直接使用 search 工具：
```markdown
web_search: site:theresanaiforthat.com "video generator" OR "image generator" OR "voice" OR "music" OR "AI agent" launched 2026
```
从搜索片段中提取未被前两步覆盖的新产品词。若查无有效内容直接跳过。

---

### 第三步：候选词筛选
汇总三环节提取的**产品名称**。
**只保留属于以下 jxp.com 核心类目的产品：**
- 🎬 AI 视频 (text-to-video, video editor, video generator)
- 🖼️ AI 图像 (text-to-image, image generator, photo editor)
- 🎵 AI 音频 (TTS, voice cloning, music generation)
- 🔤 AI 文本 (writing assistant)
- 🤖 AI Agent (autonomous agent, assistant bot)

**跳过逻辑：**
- 泛滥的 B2B SaaS、CRM、HR、开发者代码工具。
- 已经被各种大厂垄断的词（ChatGPT、Claude、Midjourney、Runway 等）。

如果在这一步结束后没有任何符合条件的词留下，使用 `message` tool 发送通知后直接跳到第五步：
- action: send
- channel: feishu
- target: user:ou_ac1b78739e30c3f7b3a2ee525f0508e4
- message: `【AI目录雷达】今天三家目录站均无高质量相关新词。`

---

### 第四步：格式化与写入

读取全局写入规则：
```bash
cat /root/.openclaw/workspace/scripts/RULES.md
```

**必须遵循的特殊写入指令：**
1. **纯产品名录入**：关键词只允许是发现的产品名称本身，**不需要**你自己创造或拼凑“需求前缀/后缀词”。就写产品词！
2. **关键词类型**：所有从本次任务挖掘出的词，`--keyword-type` 统一归为 `product`。
3. **来源与链接**：
   - `--source` 必须严格填 `Toolify` 或 `Futurepedia` 或 `TAAFT`。
   - 链接严格使用第二步提取到的真实 URL。

依据 `RULES.md` 的规范，通过下方脚本把每个通过筛选的词循环写入数据库：
```bash
python3 /root/.openclaw/workspace/scripts/write_keyword.py --keyword "<产品名>" --keyword-type "product" --source "<对应源>" --source-url "<提取的确切URL>"
```

---

### 第五步：收尾
结束本次执行，无论是否有新词产出：
```bash
python3 /root/.openclaw/workspace/scripts/update_last_task.py seo-aitool-directory
```
```

---

## 四、上线 Checklist（⚠️ Blockers ⚠️）

以下任务清单是上线的前置条件，**必须全部完成才能正式运行**：

- [x] curl 验证 `toolify.ai/new` (Jina 抓取实测包含 'Just launched' 及工具名)
- [x] curl 验证 `futurepedia.io/` (Jina 抓取实测包含 'Recently Added' 等模块)
- [x] curl 验证 `theresanaiforthat.com/new` (实测验证 Cloudflare 强拦截 connection reset，已改用 web search)
- [ ] ⚠️ **Code Blocker**：更新 `write_keyword.py`，在其 `ALLOWED_SOURCES` 白名单中显式加入 `Toolify`, `Futurepedia`, `TAAFT`，否则写入将直接抛错。
- [ ] **Data Blocker**：更新 `jobs.json` 里的 prompt 为上述 V3 的完整可执行版本。

---

## 五、预估指标
运营 1 周后评估：
- **信噪比**：抓取的关键词中，"纯域名"或无意义词段占比应 < 5%。
- **覆盖度**：产品库录入 >2 个/天 的新颖产品词。
- **稳定性**：Jina <1000 字节的 Failback 应成功捕捉拦截，实现静默失败不写假词。
