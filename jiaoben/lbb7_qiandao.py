#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LBB7 单账号签到（带金额提示）
Cron: 10 8 * * *
new Env('LBB7 单账号签到（金额版）');
"""

import os
import sys
import time
import re
import requests

# ========= 通知 =========
try:
    from notify import send
except ImportError:
    print("❌ 缺少 notify.py")
    sys.exit(1)

# ========= 配置 =========
BASE = "https://zhh.lbb7.cn/user"
SIGN_API = f"{BASE}/ajax_user.php?act=qiandao"
RECORD_URL = f"{BASE}/record.php"

COOKIE = os.getenv("LBB7_COOKIE", "").strip()

if not COOKIE:
    send("LBB7 签到失败", "❌ 未配置 LBB7_COOKIE")
    sys.exit(1)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE}/qiandao.php",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cookie": COOKIE,
}

session = requests.Session()

print("🚀 LBB7 单账号签到开始")

# ========= 1. 签到 =========
try:
    r = session.get(SIGN_API, headers=HEADERS, timeout=15)
    data = r.json()
except Exception as e:
    msg = f"❌ 签到请求失败：{e}"
    print(msg)
    send("LBB7 签到失败", msg)
    sys.exit(1)

msg_text = str(data.get("msg", "")).strip()

# ========= 状态判断 =========
if "IP今天已经签到" in msg_text:
    result = f"🚫 IP 限制：{msg_text}"
    print(result)
    send("LBB7 签到结果", result)
    sys.exit(0)

if "已经签到" in msg_text:
    result = f"📅 今日已签到"
    print(result)
    send("LBB7 签到结果", result)
    sys.exit(0)

if "成功" not in msg_text:
    result = f"⚠️ 未知返回：{msg_text}"
    print(result)
    send("LBB7 签到异常", result)
    sys.exit(0)

print("✅ 签到接口返回成功，等待入账确认…")
time.sleep(2)

# ========= 2. 查询收支明细 =========
amount = None
try:
    r = session.get(RECORD_URL, headers=HEADERS, timeout=15)
    html = r.text

    # 匹配“签到 + 金额”
    match = re.search(
        r"签到.*?([0-9]+\.[0-9]{1,2})元", html
    )
    if match:
        amount = match.group(1)
except Exception:
    pass

# ========= 3. 最终结果 =========
if amount:
    result = f"🎉 签到成功，获得 {amount} 元"
else:
    result = f"🎉 签到成功（金额未识别）"

print(result)

send(
    title="LBB7 签到成功",
    content=result
)

print("✅ 执行完成")
