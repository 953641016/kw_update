# 开发规约：`verify_release_date.py` 生产脚本规范

根据《项目说明》的架构边界，AI 智能体仅负责输出**具备可执行级别的架构方案与代码规约**，供线上 OpenClaw 环境自主完成实际迭代。

本规约旨在指导 OpenClaw 编写 `seo-radar` 的底层日期验证微服务 `verify_release_date.py`。

---

## 1. 脚本定义与基础约定
- **脚本定名**：`verify_release_date.py`
- **执行环境**：Ubuntu Server (2h4G, 位于美国节点，免除境内拉取 Jina 或外网 API 的网络墙阻碍)。
- **核心职能**：接收候选关键词，按“ProductHunt -> GitHub -> Jina+GPT4o-mini”的流水线返回首发日期。

---

## 2. 输入输出规范 (I/O)

为了与现有的 OpenClaw 体系（如 `write_keyword.py`）无缝衔接，该微服务必须严格遵循标准 CLI 传参及标准 JSON 输出范式。

### 2.1 输入参数 (argparse)
调用示例：
```bash
python3 verify_release_date.py --keyword "DeepSeek-V3"
```
必备参数：
- `--keyword`: 字符串类型。待核实发布日期的产品名称。

### 2.2 输出契约 (stdout)
**关键纪律**：微服务的 `sys.stdout` 只能用于输出最终的 JSON 结果供管道捕获。任何提示语、警告（如休眠等待打印、速率超限警告）**必须**打印到 `sys.stderr`。

最终输出 JSON 格式要求：
- **查到明确日期时**：
  ```json
  {"ok": true, "release_date": "2024-12-26", "source": "GitHub"}
  ```
- **经过四道防线依然查无此人（超级冷门/泄露爆款）**：
  ```json
  {"ok": true, "release_date": "", "source": "None"}
  ```
- **系统级硬错误（如网络断开）**：
  ```json
  {"ok": false, "error": "Jina API connection timeout"}
  ```

---

## 3. 核心机制：GPT-4o-mini 大脑提示词怎么写？

在触发第三级拦截（即免费接口没命中，动用搜索引擎兜底）时，代码中组装请求发给大模型（如 Sonnet 4.6 或 GPT-4o-mini）的 Prompt 必须做到“极度封锁幻觉”。

以下是经过 PoC 极限测试论证的**黄金提示词**标准模板：

### System Prompt (系统角色与指令边界)
```text
You are a precise data extractor. Read the provided search summary and extract the INITIAL PUBLIC RELEASE DATE of the AI product. 
Your output must strictly be in the format 'YYYY-MM-DD'. 
If no concrete date is found in the text, or if it is only a rumor with no confirmed official launch date, you must output exactly 'NULL'. 
Do not output any explanations or extra characters.
```

### User Prompt (用户数据拼装)
```text
Product Name: {keyword}

Search Snippets:
{context}
```
*(注：`{context}` 变量即为通过 `https://s.jina.ai/{keyword} official release date announcement` 抓取到的网页前 1500 字符。)*

### 提示词原理剖析
1. **身份铁皮化**：声明它是 `precise data extractor` 而不是 AI 助手，掐断闲聊欲望。
2. **格式死锁**：强制定规只输出 `YYYY-MM-DD` 字符，便于主流程脚本接收后原样计算。
3. **退路机制设定**：强制规定若无确切日期直接输出 `NULL`，以此作为“此产品极度新鲜未经报道”的最高保真信号，避免瞎编一个无关年份凑数。

---

## 4. 并发与限流标准
在线上 OpenClaw 编排调用该微服务时，脚本内必须植入如下逻辑保障长治久安：

1. **Token 注入**：`os.environ.get('GITHUB_TOKEN')` 必须非空（提升至 30次/分）。
2. **随机休眠 (Jitter)**：脚本头部强制添加 `time.sleep(random.uniform(1.5, 3.0))`，以物理性压低并发，避免 Ubuntu 宿主机 IP 被 GitHub 防火墙封杀。
