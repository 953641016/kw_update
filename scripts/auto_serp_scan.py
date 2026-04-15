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

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR    = os.path.normpath(os.path.join(SCRIPT_DIR, '..'))
CONFIG_FILE      = os.path.expanduser('~/.openclaw/openclaw.json')
STATE_FILE       = os.path.join(WORKSPACE_DIR, 'data', 'seo-radar-state.json')
FEISHU_HOST      = 'https://open.feishu.cn'
APP_TOKEN        = 'X8ozbHjDqajwGQsYeqncv5Oanrg'
TABLE_ID         = 'tblVZJ1xU51qTb2b'
INTERVAL_SECONDS = 15
DAYS_WINDOW      = 3


def load_local_serp_reports() -> dict:
    """从本地 state 读取已有的 serp_reports，作为排重主数据源"""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        return state.get('serp_reports', {})
    except (json.JSONDecodeError, IOError):
        return {}


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
    """
    本地二次过滤：
      1. 收录时间在最近 3 天内
      2. 发布日期为空 OR 在最近 3 天内
    （优先级和 Serp报告为空已由服务端过滤）
    """
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=DAYS_WINDOW)
    candidates = []
    for rec in records:
        fields = rec.get('fields', {})
        record_id = rec.get('record_id', '')
        keyword = fields.get('关键词', '')
        if not keyword:
            continue
        # 收录时间在最近 3 天内
        create_time = fields.get('收录时间')
        if create_time:
            ct_dt = ms_to_datetime(create_time)
            if ct_dt and ct_dt < cutoff:
                continue
        else:
            continue  # 无收录时间跳过
        # 发布日期为空 OR 在最近 3 天内
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

    # Step 1: 先从本地 state 读取已有报告（主数据源）
    local_reports = load_local_serp_reports()
    logger.info(f"  本地已有报告: {len(local_reports)} 个关键词")

    # Step 2: 从飞书拉取高优先级 + 报告为空的记录
    token = get_feishu_token()
    raw_records = fetch_candidate_records(token)
    logger.info(f"  飞书服务端过滤后: {len(raw_records)} 条记录")

    # Step 3: 本地二次过滤（时间条件 + 排除本地已有报告的词）
    candidates = filter_records(raw_records)
    # 排除本地 state 已有报告的关键词
    before_count = len(candidates)
    candidates = [c for c in candidates if c['keyword'] not in local_reports]
    skipped = before_count - len(candidates)
    if skipped:
        logger.info(f"  排除本地已有报告: {skipped} 个")
    logger.info(f"  最终待分析: {len(candidates)} 条")

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
