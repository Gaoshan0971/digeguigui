#!/usr/bin/env python3
"""用法: python3 write_log.py <项目> <今日工作> [遇到的问题] [明日计划]"""
import urllib.request, urllib.error, json, sys
from datetime import datetime, timezone

APP_ID = "cli_a92c12ababb8dcb1"
APP_SECRET = "6merL7g6FWs3UOTD2PXM0dpcgUxN3OyH"
APP_TOKEN = "PVHrbZHKQaolMas392Lcs7N3nZb"
TABLE_ID = "tbl2yQTNLzmAI0Dt"

PROJECT_OPTIONS = {
    "搭肩空投": "opt3aUEB69",
    "滴个龟龟": "optrh17MDL",
    "清诉心理": "opt6nXNSCp",
    "总助对话": "optDkz5LIe",
}

def main():
    if len(sys.argv) < 3:
        print("用法: python3 write_log.py <项目> <今日工作> [遇到的问题] [明日计划]")
        sys.exit(1)
    project = sys.argv[1]
    work = sys.argv[2]
    issues = sys.argv[3] if len(sys.argv) > 3 else ""
    plan = sys.argv[4] if len(sys.argv) > 4 else ""
    if project not in PROJECT_OPTIONS:
        print(f"可选: {', '.join(PROJECT_OPTIONS.keys())}")
        sys.exit(1)
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode(),
        headers={"Content-Type": "application/json"}
    )
    token = json.loads(urllib.request.urlopen(req).read())["tenant_access_token"]
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    record = {"fields": {"项目": PROJECT_OPTIONS[project], "日期": ts, "今日工作": work, "遇到的问题": issues, "明日计划": plan}}
    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
        data=json.dumps(record).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        print(f"✅ 写入成功: {project}" if resp.get("code") == 0 else f"❌ {resp}")
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.read().decode()}")

if __name__ == "__main__":
    main()
