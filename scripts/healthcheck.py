#!/usr/bin/env python3
"""滴个龟龟全链路自动巡检"""
import json, subprocess, sys, os, ssl, socket
from datetime import datetime
import sqlite3
import urllib.request

BASE = "https://api.digeguigui.com"
DB = "/home/ubuntu/digeguigui/data/digeguigui.db"
FAILS = 0

def ok(name, msg, passed=True):
    global FAILS
    icon = "✅" if passed else "❌"
    if not passed:
        FAILS += 1
    print(f"  {icon} {name}: {msg}")

def api(path):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return json.loads(r.read())

def web_get(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

# ── RUN ──
ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
print(f"=== 滴个龟龟巡检 {ts} ===\n")

print("── API ──")
try:
    d = api("/api/health")
    ok("health", f"uptime={d.get('uptime')}s", d.get("ok") and d.get("db") == "ok")
except Exception as e:
    ok("health", str(e), False)

try:
    d = api("/api/v2/stats")
    data = d["data"]
    ok("stats", f"total={data['total']} fam={data['families']} genes={data['genes']} combos={data['combos']}",
       data["total"] >= 600)
except Exception as e:
    ok("stats", str(e), False)

try:
    d = api("/api/v2/species?limit=1")
    ok("species", f"total={d.get('total','?')}", d.get("ok") and d.get("total", 0) >= 600)
except Exception as e:
    ok("species", str(e), False)

try:
    d = api("/api/v2/morphs/heavy")
    ok("morphs", f"heavy={len(d.get('data',[]))}", d.get("ok") and len(d.get("data", [])) >= 10)
except Exception as e:
    ok("morphs", str(e), False)

try:
    d = api("/api/v2/prices/species/1")
    ok("prices", "OK", d.get("ok"))
except Exception as e:
    ok("prices", str(e), False)

print("\n── Database ──")
try:
    conn = sqlite3.connect(DB)
    total = conn.execute("SELECT COUNT(*) FROM species").fetchone()[0]
    genes = conn.execute("SELECT COUNT(*) FROM morph_genes").fetchone()[0]
    ok("sqlite", f"species={total} genes={genes}", total >= 600)
    conn.close()
except Exception as e:
    ok("sqlite", str(e), False)

print("\n── System ──")
try:
    r = subprocess.run(["systemctl", "is-active", "digeguigui-api"], capture_output=True, text=True)
    ok("service", r.stdout.strip(), r.stdout.strip() == "active")
except Exception as e:
    ok("service", str(e), False)

try:
    r = subprocess.run(["systemctl", "is-active", "nginx"], capture_output=True, text=True)
    ok("nginx", r.stdout.strip(), r.stdout.strip() == "active")
except Exception as e:
    ok("nginx", str(e), False)

try:
    ctx = ssl.create_default_context()
    with socket.create_connection(("api.digeguigui.com", 443), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname="api.digeguigui.com") as ss:
            cert = ss.getpeercert()
    expiry = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    days = (expiry - datetime.utcnow()).days
    ok("ssl", f"expires {expiry.strftime('%Y-%m-%d')} ({days}d)", days > 30)
except Exception as e:
    ok("ssl", str(e), False)

try:
    stat = os.statvfs("/")
    pct = (1 - stat.f_bavail / stat.f_blocks) * 100
    ok("disk", f"{pct:.0f}% used", pct < 85)
except Exception as e:
    ok("disk", str(e), False)

try:
    with open("/proc/meminfo") as f:
        lines = f.readlines()
    total = int(lines[0].split()[1])
    avail = int(lines[2].split()[1])
    pct = (total - avail) / total * 100
    ok("mem", f"{pct:.0f}% used (avail={avail//1024}M)", pct < 90)
except Exception as e:
    ok("mem", str(e), False)

print("\n── External ──")
try:
    d = web_get("https://api.gbif.org/v1/species/match?name=Testudo")
    ok("GBIF", "reachable", "usageKey" in d)
except Exception as e:
    ok("GBIF", str(e), False)

try:
    d = web_get("https://api.inaturalist.org/v1/taxa?q=Testudo&per_page=1",
                headers={"Referer": "https://www.inaturalist.org"})
    ok("iNat", "reachable", d.get("total_results", 0) > 0)
except Exception as e:
    ok("iNat", str(e), False)

print(f"\n── {FAILS} 项失败 ──")
sys.exit(1 if FAILS else 0)
