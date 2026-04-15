# 迭代方案：seo-china 信号源扩展（Image 品类补全）

**日期：2026-04-02**
**版本：V2（审查后修订）**
**关联调查：[调查报告-中国信号源Image-Audio扩展](file:///Users/zhangjian/project/keyword/docs/调查报告-中国信号源Image-Audio扩展.md)**

---

## 一、背景

当前 `seo-china` 的 4 个官方站全部偏 Video 品类（Seed/Kling/海螺/Vidu），Image/Audio 维度空缺，空跑率 44%、日均产词 0.94。

经两轮 13 站实测 + 审查，确定 **2 个变更**立即上线：

| 变更 | 站点 | 品类覆盖 | Jina 实测 | 理由 |
|------|------|---------|----------|------|
| **替换** hailuoai.video | `minimaxi.com` | Video + Speech + Music + Text | ✅ 21KB | hailuoai 的超集，一页覆盖 5 品类 |
| **新增** | `wanxiang.aliyun.com` | Image | ✅ 3KB | 阿里 Image 主力，填补品类空白 |

### 审查中排除的站点

| 站点 | 排除原因 |
|------|---------|
| **mureka.ai** | ❌ SPA 内容差（30KB 仅提取 "V9" 一个标识）；搜索量近零，SEO 回报极低 |
| **hunyuan.tencent.com** | ⏳ 备选，待本轮上线观察 2 周后再决定是否追加 |

---

## 二、执行内容

### 唯一变更：更新 `jobs.json` 中 seo-china 的 prompt

- **无需修改** `write_keyword.py` 或 `SOURCE_MAP`（新站来源统一归入现有的 `中国官方站`）
- **同步更新** `TOOLS.md` 中记录的官方站 URL（`tongyi.aliyun.com/wanxiang` → `wanxiang.aliyun.com`）

---

## 三、完整新 Prompt

请将 seo-china job 的 `payload.message` **整体替换**为以下内容：

```
你是 jxp.com 的 SEO 关键词侦察员，专门负责监控**中国 AI 模型**的最新动态。jxp.com 覆盖 Video/Image/Audio/Text 四类 AI 生成工具。

## 任务：检测中国 AI 模型是否有新发布

### 第一步：获取当前 UTC 日期

```bash
date -u +%Y-%m-%d
```

---

### 第二步：抓取数据源

**① 官方站模型列表（主力信号）**

```bash
curl -s "https://r.jina.ai/https://seed.bytedance.com/en/models" --max-time 15
curl -s "https://r.jina.ai/https://klingai.com" --max-time 15
curl -s "https://r.jina.ai/https://www.minimaxi.com" --max-time 15
curl -s "https://r.jina.ai/https://www.vidu.studio" --max-time 15
curl -s "https://r.jina.ai/https://wanxiang.aliyun.com" --max-time 15
```

从页面提取**模型名称+版本号**（如 Seedance 2.0、Kling 3.0）。

**各站提取要点：**
- **MiniMax 官网**（minimaxi.com）：全栈模型矩阵，提取带 NEW 标签的最新版本。覆盖 Text (M2.7) / Speech (2.6) / Video (Hailuo 2.3) / Music (2.5+)，精化为英文产品词（如 `MiniMax Speech 2.6`、`Hailuo 2.3`）
- **通义万相**（wanxiang.aliyun.com）：提取模型名+版本号（如页面中的"万相2.7"），精化为英文产品词（如 `Wan 2.7`）。注意：Wan 系列词大概率已被 seo-platforms 提前收录，dedup 过滤后属正常现象，重点关注新版本升级（如 Wan 3.0）

**② 量子位最新资讯（中文媒体首发报道）**

```bash
curl -s "https://r.jina.ai/https://www.qbitai.com/category/%e8%b5%84%e8%ae%af" --max-time 15
```

从文章标题中提取**新发布的 AI 生成工具/模型名称**（视频/图像/音频类）。
忽略：融资新闻、政策资讯、企业合作、非生成类 AI 产品。

---

### 第三步：去重检查（关键：决定是否继续）

合并两个来源提取的所有候选词，批量去重：

```bash
python3 /root/.openclaw/workspace/scripts/dedup_check.py "模型名1" "模型名2" ...
```

**判断逻辑：**

- 若所有候选词均已在库 → 用 `message` 工具发送简报，然后结束任务：
  - action: send
  - channel: feishu
  - target: user:ou_ac1b78739e30c3f7b3a2ee525f0508e4
  - message 格式：
    ```
    【中国AI雷达 · MM-DD】📭 今日无新模型
    • 官方站：Seedance/Kling/MiniMax/Vidu/万相 均已在库
    • 量子位：无新发布
    ```
- 若有新词出现 → 继续第四步

---

### 第四步：知乎补充细节（仅新词触发，严格限制）

```
web_search: site:zhihu.com "新模型名" 使用体验
```

⚠️ **知乎搜索限制：**
- 每个新词最多 **1次** web_search
- 仅用于提取**功能描述词**（用户怎么描述这个工具）
- **禁止用于验证发布日期**
- 搜不到结果 → 跳过，不重试

**发布日期判断规则（禁止额外 web_search 验证）：**
- 官方站页面能看到版本号 → 认为已发布，状态 ✅正式可用
- 量子位文章发布日期即为发布日期（jina.ai 返回的内容含日期）
- 无法确认 → ⏳待评估，直接使用，不搜索

---

### 第五步：完整分析（仅新词触发）


#### ⚠️ 发布日期填写规则（必须遵守）
- 从来源内容能**直接看到**具体日期（如"2026年3月发布"、版本发布公告）→ 填入 `--release-date YYYY-MM-DD`
- 无法从来源直接确认 → **留空（不传 --release-date 参数），禁止估算或猜测**

#### ⚠️ 关键词类型判断规则（必须遵守）
- 产品名称（Seedance 3.0、Kling 4.0）→ `--keyword-type product`
- 通用功能描述词 → `--keyword-type demand`
- 技术方法名 → `--keyword-type technical`

**来源统一填「中国官方站」**

分析规范（关键词精化/去重/Trends/SERP/写入飞书/收尾）：
```bash
cat /root/.openclaw/workspace/scripts/RULES.md
```

---

### 收尾：更新运行时间戳

任务完成后执行（无论本轮是否有新词写入）：

```bash
python3 /root/.openclaw/workspace/scripts/update_last_task.py seo-china
```
```

---

## 四、变更摘要（Diff）

### 第二步 ① 官方站 curl 列表

```diff
 curl -s "https://r.jina.ai/https://seed.bytedance.com/en/models" --max-time 15
 curl -s "https://r.jina.ai/https://klingai.com" --max-time 15
-curl -s "https://r.jina.ai/https://hailuoai.video" --max-time 15
+curl -s "https://r.jina.ai/https://www.minimaxi.com" --max-time 15
 curl -s "https://r.jina.ai/https://www.vidu.studio" --max-time 15
+curl -s "https://r.jina.ai/https://wanxiang.aliyun.com" --max-time 15
```

### 第二步 新增提取要点

```diff
 从页面提取**模型名称+版本号**（如 Seedance 2.0、Kling 3.0）。
+
+**各站提取要点：**
+- **MiniMax 官网**（minimaxi.com）：全栈模型矩阵，提取带 NEW 标签的最新版本...
+- **通义万相**（wanxiang.aliyun.com）：提取模型名+版本号，精化为英文产品词。
+  注意：Wan 系列词大概率已被 seo-platforms 提前收录，dedup 过滤后属正常现象
```

### 第三步 空跑通知消息

```diff
-• 官方站：Seedance/Kling/海螺/Vidu 均已在库
+• 官方站：Seedance/Kling/MiniMax/Vidu/万相 均已在库
```

---

## 五、预期效果

| 指标 | 当前 | 变更后预期 | 计算依据 |
|------|------|-----------|---------|
| 官方站数量 | 4 站（纯 Video） | 5 站（4 Video/Speech/Music + 1 Image） | +1 净增（替换 1 + 新增 1） |
| 品类覆盖 | Video 为主 | Video + Image + Speech + Music | MiniMax 全栈 + 万相 Image |
| 空跑率 | ~44% | ~60% | 5 站月更新约 6-8 次 ÷ 30 天，扣除 dedup 已在库词 |
| 日均产词 | ~0.94 | ~0.8（稳态） | MiniMax 补齐 Speech/Music 存量后回归常态 |

> 空跑率可能反升的原因：MiniMax 替换 hailuoai.video 后，首跑消化 Speech/Music 存量版本会有短期增量，但稳态下 5 站的版本发布频率（约 4-5 天/次）决定了空跑率理论下限在 60% 附近。这在预期范围内——seo-china 的核心价值是**不漏关键版本升级**，而非日均高产。

---

## 六、附加变更：TOOLS.md 同步

更新 `openclaw/workspace/TOOLS.md` 中 seo-china 的官方站清单描述：

```diff
-**官方站清单：** seed.bytedance.com/en/models / klingai.com / hailuoai.video / vidu.studio / tongyi.aliyun.com/wanxiang / hunyuan.tencent.com
+**官方站清单：** seed.bytedance.com/en/models / klingai.com / minimaxi.com / vidu.studio / wanxiang.aliyun.com
```

---

## 七、后续观察计划

上线后观察 2 周（约 14 次执行），评估：

1. **MiniMax 覆盖度**：Speech/Music/Text 品类是否有新版本被首次捕获
2. **万相空跑率**：连续 4 次运行均被 seo-platforms dedup 全量过滤 → 考虑从 seo-china 移除，降为仅 seo-platforms 覆盖
3. **是否追加音乐源**：若 MiniMax 的 Music 品类覆盖不足，再评估 hunyuan.tencent.com 或其他方案
