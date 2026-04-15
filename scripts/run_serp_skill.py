#!/usr/bin/env python3
"""
run_serp_skill.py - 桥接 openclaw 与 serp_skill 的适配脚本

通过 subprocess 调用 serp_skill Pipeline，彻底隔离运行环境。
从 stdout 日志中解析飞书链接，先更新本地 state，再同步飞书。

数据流：serp_skill → 解析结果 → 写入本地 state → 回写飞书多维表格

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
import time
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
    """回写飞书多维表格的 Serp分析报告 字段"""
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


def save_to_local_state(keyword: str, feishu_url: str, report_path: str):
    """
    先更新本地 state（serp_reports 字典），再同步飞书。
    使用与 write_keyword.py 相同的 locked_state 模式确保原子写入。
    """
    # 尝试 import locked_state（服务器上可用）
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from state_io import locked_state
        with locked_state() as state:
            sr = state.setdefault('serp_reports', {})
            sr[keyword] = {
                'feishu_url': feishu_url or '',
                'report_path': report_path or '',
                'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        logger.info(f"📝 本地 state 已更新: serp_reports['{keyword}']")
    except ImportError:
        # 本地开发环境无 state_io（无 fcntl），直接读写
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                state = json.load(f)
        else:
            state = {}
        sr = state.setdefault('serp_reports', {})
        sr[keyword] = {
            'feishu_url': feishu_url or '',
            'report_path': report_path or '',
            'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        logger.info(f"📝 本地 state 已更新（非锁模式）: serp_reports['{keyword}']")


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
        cwd=serp_dir,
        timeout=600
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

        # Step 1: 先更新本地 state
        if feishu_url or md_path:
            save_to_local_state(args.keyword, feishu_url, md_path)

        # Step 2: 再同步飞书多维表格
        record_updated = False
        if record_id and feishu_url:
            try:
                update_serp_report_field(record_id, feishu_url)
                record_updated = True
            except Exception as e:
                logger.error(f"飞书回写失败（本地 state 已更新）: {e}")

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
