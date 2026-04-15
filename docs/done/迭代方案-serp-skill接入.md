# serp_skill 接入方案 V3 — 完整执行指南

> 本文档供你（openclaw agent）在服务器上逐步执行。**不修改 serp_skill 任何原始代码**，全部通过外部适配脚本完成。

> ⚠️ **分阶段执行说明**：
> - **阶段 1（立即执行）**：第一~三章 — 安装 serp_skill + 部署桥接脚本 `run_serp_skill.py` + 更新 TOOLS.md
> - **阶段 2（暂不执行，后续通知后再开启）**：第四~五章 — 部署 `auto_serp_scan.py` 自动扫描脚本 + 创建 cron job

> ⚠️ **脚本版本说明**：本文档内嵌的脚本代码仅供参考阅读。**执行时以独立脚本文件为准**（`scripts/run_serp_skill.py`、`scripts/auto_serp_scan.py`），独立文件包含 `save_to_local_state` 和本地排重等最新功能。

---

## 一、安装 serp_skill（Git Submodule）

### Step 1：添加子模块

```bash
cd /root/.openclaw/workspace

# 添加 git submodule
git submodule add https://github.com/953641016/serp_skill.git serp_skill

# 配置远程 URL（含只读 PAT，用于后续 git pull 更新）
# PAT 从 serp-skill接入需求.md 获取，禁止写入本文档
cd serp_skill
git remote set-url origin https://953641016:<PAT>@github.com/953641016/serp_skill.git
cd ..
```

> ⚠️ **安全提示**：PAT 见 `docs/serp-skill接入需求.md` 第 19 行，禁止在其他文档/代码中明文记录。安装完成后建议：
> 1. 将 remote URL 改回不含 token 的格式：`git remote set-url origin https://github.com/953641016/serp_skill.git`
> 2. 后续需要 pull 时临时设置：`git -c credential.helper='!echo password=<PAT>' pull`

### Step 2：安装 Python 依赖

```bash
cd /root/.openclaw/workspace/serp_skill
pip install -r requirements.txt
cd ..
```

### Step 3：验证 .env 配置

serp_skill 使用自己的 `.env` 文件（`/root/.openclaw/workspace/serp_skill/.env`），确认以下关键配置：

```bash
cat /root/.openclaw/workspace/serp_skill/.env | grep -E '^(FEISHU_ENABLED|SEMRUSH_MODE|SERPER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY)'
```

必须满足：
- `FEISHU_ENABLED=true`（飞书上传开启）
- `SEMRUSH_MODE=api`（轻量模式，适合 2H4G 服务器）
- 四个 API Key（SERPER / OPENAI / ANTHROPIC / GEMINI）均有值

### Step 4：验证安装成功

```bash
cd /root/.openclaw/workspace/serp_skill
python3 -c "from main_v2 import run_v2_pipeline; print('✅ serp_skill import OK')"
cd ..
```

### Step 5：提交 submodule 注册

```bash
cd /root/.openclaw/workspace
git add .gitmodules serp_skill
git commit -m "feat: add serp_skill as git submodule"
```

---

## 二、部署适配脚本

以下两个脚本已由我准备好，需要你创建到服务器的 `scripts/` 目录下。

### Step 6：创建 `scripts/run_serp_skill.py`

桥接脚本，职责：通过 subprocess 调用 serp_skill Pipeline（进程隔离）→ 从日志解析飞书链接 → 回写多维表格。

将以下完整内容写入 `/root/.openclaw/workspace/scripts/run_serp_skill.py`：

```python
#!/usr/bin/env python3
"""
run_serp_skill.py - 桥接 openclaw 与 serp_skill 的适配脚本

通过 subprocess 调用 serp_skill Pipeline，彻底隔离运行环境。
从 stdout 日志中解析飞书链接，回写多维表格。

用法：
  python3 run_serp_skill.py --keyword "Veo 3"
  python3 run_serp_skill.py --keyword "Veo 3" --record-id recXXX
  python3 run_serp_skill.py --keyword "Veo 3" --auto-record

输出 JSON：
  {"ok": true, "keyword": "Veo 3", "feishu_url": "https://...", "report_path": "...", "record_updated": true}
  {"ok": false, "keyword": "Veo 3", "error": "..."}
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── 配置 ──
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR  = os.path.normpath(os.path.join(SCRIPT_DIR, '..'))
SERP_SKILL_DIR = os.path.join(WORKSPACE_DIR, 'serp_skill')
CONFIG_FILE    = os.path.expanduser('~/.openclaw/openclaw.json')
STATE_FILE     = os.path.join(WORKSPACE_DIR, 'data', 'seo-radar-state.json')
FEISHU_HOST    = 'https://open.feishu.cn'
APP_TOKEN      = 'X8ozbHjDqajwGQsYeqncv5Oanrg'
TABLE_ID       = 'tblVZJ1xU51qTb2b'
FIELD_SERP_REPORT = 'Serp分析报告'  # 字段 ID: fldvqQobQj


def get_feishu_token() -> str:
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    fc = cfg['channels']['feishu']
    req = urllib.request.Request(
        f'{FEISHU_HOST}/open-apis/auth/v3/tenant_access_token/internal',
        data=json.dumps({'app_id': fc['appId'], 'app_secret': fc['appSecret']}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=10) as resp:
        r = json.loads(resp.read())
    if r.get('code') != 0:
        raise RuntimeError(f"飞书 token 获取失败: {r}")
    return r['tenant_access_token']


def update_serp_report_field(record_id: str, feishu_url: str):
    token = get_feishu_token()
    url = f'{FEISHU_HOST}/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}'
    fields = {FIELD_SERP_REPORT: feishu_url}
    req = urllib.request.Request(
        url, data=json.dumps({'fields': fields}).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
        method='PUT')
    with urllib.request.urlopen(req, timeout=15) as resp:
        r = json.loads(resp.read())
    if r.get('code') != 0:
        raise RuntimeError(f"飞书更新失败: {r}")
    logger.info(f"✅ 飞书字段已更新: record_id={record_id}")


def lookup_record_id(keyword: str) -> str:
    """从 seo-radar-state.json 的 keyword_records 查找 record_id"""
    if not os.path.exists(STATE_FILE):
        return ''
    with open(STATE_FILE) as f:
        state = json.load(f)
    return state.get('keyword_records', {}).get(keyword, '')


def run_serp_pipeline(keyword: str):
    """
    通过 subprocess 调用 serp_skill，彻底隔离运行环境。
    从 stdout/stderr 日志中解析飞书链接和报告路径。
    返回 (md_path, feishu_url)
    """
    serp_dir = os.path.abspath(SERP_SKILL_DIR)
    if not os.path.isdir(serp_dir):
        raise FileNotFoundError(f"serp_skill 目录不存在: {serp_dir}")

    cmd = [sys.executable, os.path.join(serp_dir, 'main_v2.py'), keyword]
    logger.info(f"  调用: {' '.join(cmd)}")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=serp_dir,  # 在 serp_skill 目录下执行，确保 .env 和相对路径正确
        timeout=600     # 单个关键词最长 10 分钟
    )

    all_output = (proc.stderr or '') + '\n' + (proc.stdout or '')

    # 解析飞书链接
    feishu_url = None
    feishu_match = re.search(r'飞书文档[链接]?[:：]\s*(https://\S+)', all_output)
    if feishu_match:
        feishu_url = feishu_match.group(1)

    # 解析报告路径
    md_path = None
    path_match = re.search(r'(?:Report|Renamed to)[:：]\s*(/\S+\.md)', all_output)
    if path_match:
        md_path = path_match.group(1)

    if proc.returncode != 0 and not feishu_url:
        last_lines = all_output.strip().split('\n')[-5:]
        raise RuntimeError(f"Pipeline 退出码 {proc.returncode}:\n" + '\n'.join(last_lines))

    return md_path, feishu_url


def main():
    parser = argparse.ArgumentParser(description='桥接 openclaw 与 serp_skill')
    parser.add_argument('--keyword', required=True)
    parser.add_argument('--record-id', default='')
    parser.add_argument('--auto-record', action='store_true',
                        help='自动从 seo-radar-state.json 的 keyword_records 查找 record_id')
    args = parser.parse_args()

    record_id = args.record_id
    if not record_id and args.auto_record:
        record_id = lookup_record_id(args.keyword)
        if record_id:
            logger.info(f"Auto lookup record_id: {record_id}")
        else:
            logger.warning(f"未在 state 中找到 '{args.keyword}' 的 record_id")

    try:
        logger.info(f"🚀 开始 SERP 分析: '{args.keyword}'")
        md_path, feishu_url = run_serp_pipeline(args.keyword)

        if md_path:
            logger.info(f"📄 报告路径: {md_path}")
        if feishu_url:
            logger.info(f"🔗 飞书链接: {feishu_url}")

        record_updated = False
        if record_id and feishu_url:
            try:
                update_serp_report_field(record_id, feishu_url)
                record_updated = True
            except Exception as e:
                logger.error(f"飞书回写失败: {e}")

        result = {
            'ok': True, 'keyword': args.keyword,
            'report_path': md_path, 'feishu_url': feishu_url,
            'record_id': record_id, 'record_updated': record_updated
        }
    except Exception as e:
        logger.error(f"Pipeline 执行失败: {e}")
        result = {'ok': False, 'keyword': args.keyword, 'error': str(e)}

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result.get('ok') else 1)


if __name__ == '__main__':
    main()
```

### Step 7：创建 `scripts/auto_serp_scan.py`（⏸️ 阶段 2，暂不执行）

> ⚠️ **此步骤属于阶段 2，当前不执行。** 等收到明确通知后再部署此脚本和对应的 cron job。

自动扫描脚本，职责：从飞书表筛选候选关键词 → 逐个触发 `run_serp_skill.py`。

将以下完整内容写入 `/root/.openclaw/workspace/scripts/auto_serp_scan.py`：

```python
#!/usr/bin/env python3
"""
auto_serp_scan.py - 自动扫描飞书表，筛选待分析关键词，逐个触发 SERP 分析

筛选条件（AND）：
  1. 优先级 = 🔴 高
  2. 收录时间在最近 3 天内
  3. Serp分析报告 字段为空
  4. 发布日期为空 OR 在最近 3 天内

用法：
  python3 auto_serp_scan.py            # 扫描 + 执行
  python3 auto_serp_scan.py --dry-run  # 仅扫描不执行
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE   = os.path.expanduser('~/.openclaw/openclaw.json')
FEISHU_HOST   = 'https://open.feishu.cn'
APP_TOKEN     = 'X8ozbHjDqajwGQsYeqncv5Oanrg'
TABLE_ID      = 'tblVZJ1xU51qTb2b'
INTERVAL_SECONDS = 15
DAYS_WINDOW      = 3


def get_feishu_token() -> str:
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    fc = cfg['channels']['feishu']
    req = urllib.request.Request(
        f'{FEISHU_HOST}/open-apis/auth/v3/tenant_access_token/internal',
        data=json.dumps({'app_id': fc['appId'], 'app_secret': fc['appSecret']}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=10) as resp:
        r = json.loads(resp.read())
    if r.get('code') != 0:
        raise RuntimeError(f"飞书 token 获取失败: {r}")
    return r['tenant_access_token']


def fetch_candidate_records(token: str) -> list:
    """
    服务端过滤：优先级=🔴高 且 Serp分析报告 为空
    时间条件在本地二次过滤（飞书 filter 不支持动态日期计算）
    """
    filter_body = {
        "filter": {
            "conjunction": "and",
            "conditions": [
                {"field_name": "优先级", "operator": "is", "value": ["🔴 高"]},
                {"field_name": "Serp分析报告", "operator": "isEmpty"}
            ]
        },
        "page_size": 500
    }
    records, page_token = [], ''
    while True:
        url = f'{FEISHU_HOST}/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/search'
        if page_token:
            filter_body['page_token'] = page_token
        req = urllib.request.Request(
            url, data=json.dumps(filter_body).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
            method='POST')
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        if data.get('code') != 0:
            raise RuntimeError(f"飞书查询失败: {data}")
        records.extend(data.get('data', {}).get('items', []))
        if not data.get('data', {}).get('has_more'):
            break
        page_token = data['data'].get('page_token', '')
    return records


def ms_to_datetime(ms_val):
    if isinstance(ms_val, (int, float)) and ms_val > 0:
        return datetime.fromtimestamp(ms_val / 1000, tz=timezone.utc)
    return None


def filter_records(records: list) -> list:
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=DAYS_WINDOW)
    candidates = []
    for rec in records:
        fields = rec.get('fields', {})
        record_id = rec.get('record_id', '')
        keyword = fields.get('关键词', '')
        if not keyword:
            continue
        # 条件 2: Serp分析报告为空
        serp_report = fields.get('Serp分析报告', '')
        if serp_report and str(serp_report).strip():
            continue
        # 条件 1: 收录时间在最近 3 天内
        create_time = fields.get('收录时间')
        if create_time:
            ct_dt = ms_to_datetime(create_time)
            if ct_dt and ct_dt < cutoff:
                continue
        else:
            continue
        # 条件 3: 发布日期为空 OR 在最近 3 天内
        release_date = fields.get('发布日期')
        if release_date:
            rd_dt = ms_to_datetime(release_date)
            if rd_dt and rd_dt < cutoff:
                continue
        candidates.append({
            'record_id': record_id,
            'keyword': keyword,
            'create_time': str(ms_to_datetime(create_time)) if create_time else '',
            'release_date': str(ms_to_datetime(release_date)) if release_date else '(空)',
        })
    return candidates


def run_serp_for_keyword(keyword: str, record_id: str) -> dict:
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'run_serp_skill.py'),
           '--keyword', keyword, '--record-id', record_id]
    logger.info(f"  执行: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        stdout_lines = proc.stdout.strip().split('\n')
        if stdout_lines:
            try:
                return json.loads(stdout_lines[-1])
            except json.JSONDecodeError:
                pass
        return {'ok': proc.returncode == 0, 'keyword': keyword,
                'stdout': proc.stdout[-500:] if proc.stdout else '',
                'stderr': proc.stderr[-500:] if proc.stderr else ''}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'keyword': keyword, 'error': 'Timeout (600s)'}
    except Exception as e:
        return {'ok': False, 'keyword': keyword, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    logger.info("=== auto_serp_scan 开始 ===")
    token = get_feishu_token()
    raw_records = fetch_candidate_records(token)
    logger.info(f"  服务端过滤后: {len(raw_records)} 条记录")

    candidates = filter_records(raw_records)
    logger.info(f"  本地过滤后: {len(candidates)} 条待分析")

    if not candidates:
        logger.info("📭 无需分析的关键词")
        print(json.dumps({'summary': {'total': 0, 'analyzed': 0, 'success': 0, 'failed': 0}},
                         ensure_ascii=False))
        return

    for i, c in enumerate(candidates, 1):
        logger.info(f"  [{i}] {c['keyword']}  (record={c['record_id']}, "
                    f"收录={c['create_time']}, 发布={c['release_date']})")

    if args.dry_run:
        logger.info("=== DRY RUN 模式 ===")
        print(json.dumps({'dry_run': True, 'candidates': candidates, 'count': len(candidates)},
                         ensure_ascii=False))
        return

    results, success_count, fail_count = [], 0, 0
    for i, c in enumerate(candidates):
        logger.info(f"\n[{i+1}/{len(candidates)}] 分析: {c['keyword']}")
        result = run_serp_for_keyword(c['keyword'], c['record_id'])
        results.append(result)
        if result.get('ok'):
            success_count += 1
            logger.info(f"  ✅ 成功: {result.get('feishu_url', '')}")
        else:
            fail_count += 1
            logger.error(f"  ❌ 失败: {result.get('error', 'unknown')}")
        if i < len(candidates) - 1:
            logger.info(f"  ⏳ 等待 {INTERVAL_SECONDS} 秒...")
            time.sleep(INTERVAL_SECONDS)

    summary = {'total': len(candidates), 'analyzed': len(results),
               'success': success_count, 'failed': fail_count, 'results': results}
    logger.info(f"\n=== 汇总: 总计 {len(candidates)} 词, 成功 {success_count}, 失败 {fail_count} ===")
    print(json.dumps({'summary': summary}, ensure_ascii=False))


if __name__ == '__main__':
    main()
```

---

## 三、更新 TOOLS.md

在 `/root/.openclaw/workspace/TOOLS.md` 的 `## SEO 雷达 Skill 状态说明` 段落之后（`---` 分割线后、`## What Goes Here` 之前），插入以下段落：

```markdown
## SERP 竞品分析（serp_skill）

- **安装路径：** `/root/.openclaw/workspace/serp_skill/`（Git Submodule）
- **桥接脚本：** `scripts/run_serp_skill.py`
- **自动扫描：** `scripts/auto_serp_scan.py`（cron 每日 UTC 00:02 / 北京 08:02）

### 手动触发

```bash
# 分析关键词 + 回写飞书多维表格（指定 record_id）
python3 /root/.openclaw/workspace/scripts/run_serp_skill.py \
  --keyword "Veo 3" --record-id recXXX

# 自动从 state 文件查找 record_id 并回写
python3 /root/.openclaw/workspace/scripts/run_serp_skill.py \
  --keyword "Veo 3" --auto-record

# 仅分析（不回写表格）
python3 /root/.openclaw/workspace/scripts/run_serp_skill.py --keyword "Veo 3"
```

### 自动触发（cron: seo-serp-analysis）

每日 UTC 00:02 自动扫描飞书表，筛选条件（AND 同时满足）：
1. 优先级 = 🔴 高
2. 收录时间在最近 3 天内
3. `Serp分析报告` 字段为空
4. 发布日期为空 OR 在最近 3 天内

逐词执行，每词间隔 15 秒。

```bash
python3 /root/.openclaw/workspace/scripts/auto_serp_scan.py --dry-run  # 仅扫描
python3 /root/.openclaw/workspace/scripts/auto_serp_scan.py            # 扫描+执行
```

### 输出

```json
{"ok": true, "keyword": "Veo 3", "feishu_url": "https://...", "report_path": "...", "record_updated": true}
```

### 飞书回写字段

`Serp分析报告` (fldvqQobQj) — 保存飞书文档 URL

### 耗时

单个关键词约 3-8 分钟（含 SERP 抓取 + Semrush + 三模型串行分析 + 飞书上传）

### 更新 serp_skill

```bash
cd /root/.openclaw/workspace/serp_skill && git pull origin main
pip install -r requirements.txt  # 有新依赖时
```

### 更新 GitHub PAT（Token 过期时）

```bash
cd /root/.openclaw/workspace/serp_skill
git remote set-url origin https://953641016:<NEW_PAT>@github.com/953641016/serp_skill.git
```
```

---

## 四、创建 Cron Job（⏸️ 阶段 2，暂不执行）

> ⚠️ **此章节属于阶段 2，当前不执行。** 等阶段 1 验证通过、收到明确通知后再创建此 cron job。

使用 openclaw 的 cron 管理功能，创建以下 cron job：

```json
{
  "name": "seo-serp-analysis",
  "description": "北京08:02 自动SERP竞品分析（高优先级+近3天新词）",
  "enabled": true,
  "schedule": {
    "kind": "cron",
    "expr": "2 0 * * *",
    "tz": "UTC"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "执行每日 SERP 自动分析扫描。\n\n```bash\npython3 /root/.openclaw/workspace/scripts/auto_serp_scan.py\n```\n\n将脚本输出作为你的回复内容直接返回。\n\n如果有成功分析的关键词，用 `message` 工具推送汇总给 `user:ou_ac1b78739e30c3f7b3a2ee525f0508e4`：\n```\n【SERP分析 · YYYY-MM-DD】\n✅ 成功 N 个: 关键词1, 关键词2...\n❌ 失败 M 个: 关键词X (原因)\n📄 飞书报告链接已自动回写到多维表格\n```\n\n如果无候选词（输出 total=0），回复 HEARTBEAT_OK 即可，不推送消息。",
    "timeoutSeconds": 3600,
    "lightContext": true
  },
  "delivery": {
    "mode": "none",
    "channel": "last"
  }
}
```

> **创建方式**：在飞书主会话中告诉 openclaw 创建此 cron job，或直接编辑 `/root/.openclaw/cron/jobs.json` 追加此条目。

---

## 五、验证清单

完成以上步骤后，按顺序验证：

```bash
# 1. 验证 submodule
cd /root/.openclaw/workspace/serp_skill
python3 -c "from main_v2 import run_v2_pipeline; print('✅ import OK')"

# 2. 验证桥接脚本参数
python3 /root/.openclaw/workspace/scripts/run_serp_skill.py --help

# 3. 验证自动扫描（dry-run）
python3 /root/.openclaw/workspace/scripts/auto_serp_scan.py --dry-run

# 4. 端到端测试（选一个高优先级关键词）
python3 /root/.openclaw/workspace/scripts/run_serp_skill.py \
  --keyword "测试关键词" --auto-record
```

验证成功后，检查飞书多维表格对应记录的 `Serp分析报告` 字段是否已填充文档链接。

---

## 六、文件变更汇总

| 操作 | 路径 | 说明 |
|:---|:---|:---|
| **[NEW]** git submodule | `workspace/serp_skill/` | 从 GitHub 克隆，不改内部代码 |
| **[NEW]** 适配脚本 | `workspace/scripts/run_serp_skill.py` | 桥接调用 + 飞书回写 |
| **[NEW]** 适配脚本 | `workspace/scripts/auto_serp_scan.py` | 条件扫描 + 逐词触发 |
| **[MODIFY]** 配置 | `workspace/TOOLS.md` | 新增 serp_skill 说明段落 |
| **[NEW]** cron job | `seo-serp-analysis` | UTC 00:02 自动触发 |

---

## 七、PAT Token 安全说明

> ⚠️ PAT 不在本文档中记录。源头见 `docs/serp-skill接入需求.md` 第 19 行。

**安装后建议**：将 remote URL 恢复为不含 token 的格式，避免 `.git/config` 泄漏：
```bash
cd /root/.openclaw/workspace/serp_skill
git remote set-url origin https://github.com/953641016/serp_skill.git
```

**Token 过期后更新方法**：
```bash
cd /root/.openclaw/workspace/serp_skill
# 临时使用新 PAT 拉取
git remote set-url origin https://953641016:<新PAT>@github.com/953641016/serp_skill.git
git pull
# 拉取后立即恢复
git remote set-url origin https://github.com/953641016/serp_skill.git
```

---

## 数据流图

```
auto_serp_scan.py（cron 每日 UTC 00:02）
  │
  ├── 1. 读本地 state → serp_reports（排除已有报告）
  ├── 2. 查飞书：优先级=高 + Serp分析报告 isEmpty
  ├── 3. 本地过滤：收录时间≤3天 + 发布日期空或≤3天
  │
  ▼  逐词调用，间隔 15 秒
run_serp_skill.py --keyword "xxx" --record-id recYYY
  │
  ├── subprocess.run(python3 main_v2.py "xxx", cwd=serp_skill/)
  │     │  （独立进程，完全隔离）
  │     ├── SERP 抓取 (Serper API)
  │     ├── GPT-4o 竞品过滤
  │     ├── Jina 页面抓取 + Semrush 外链
  │     ├── Gemini → Claude → GPT-5.4 三阶段分析
  │     ├── 本地保存 report/
  │     └── 飞书文档上传 → 日志输出 "📄 飞书文档: https://..."
  │
  ├── 正则解析 stderr/stdout → feishu_url + md_path
  │
  ├── Step 1: save_to_local_state()  ← 先写本地 state
  │     └── state['serp_reports']['xxx'] = {feishu_url, report_path, updated_at}
  │
  ├── Step 2: update_serp_report_field()  ← 再同步飞书
  │     └── PUT 飞书 API → Serp分析报告 = feishu_url
  │
  └── 输出 JSON: {"ok": true, "feishu_url": "https://..."}
```

