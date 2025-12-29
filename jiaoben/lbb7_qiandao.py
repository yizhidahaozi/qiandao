#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LBB7 单账号签到（访问触发兜底版）
"""

import os
import re
import sys
import time
import requests

try:
    from notify import send
except ImportError:
    print("❌ notify.py 不存在")
    sys.exit(1)

COOKIE = os.getenv("LBB7_COOKIE", "").strip()
if not COOKIE:
    send("LBB7 签到失败", "❌ 未配置 Cookie")
    sys.exit(1)

BASE = "https://zhh.lbb7.cn/user"
QIADAO = f"{BASE}/qiandao.php"
RECORD = f"{BASE}/record.php"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cookie": COOKIE,
}

s = requests.Session()
s.headers.update(headers)

print("🚀 LBB7 单账号签到开始（访问触发模式）")

# 1️⃣ 访问签到页
try:
    r = s.get(QIADAO, timeout=15)
    r.raise_for_status()
except Exception as e:
    msg = f"❌ 签到页访问失败：{e}"
    print(msg)
    send("LBB7 签到失败", msg)
    sys.exit(1)

time.sleep(2)

# 2️⃣ 查询收支明细，判断是否入账
try:
    r = s.get(RECORD, timeout=15)
    text = r.text
except Exception as e:
    msg = f"❌ 收支页面访问失败：{e}"
    print(msg)
    send("LBB7 签到失败", msg)
    sys.exit(1)

# 3️⃣ 判断结果
if "今日已签到" in text:
    result = "📅 今日已签到"
elif re.search(r"签到.*?([0-9]+\.[0-9]{1,2})元", text):
    amount = re.search(r"签到.*?([0-9]+\.[0-9]{1,2})元", text).group(1)
    result = f"🎉 签到成功，获得 {amount} 元"
else:
    result = "⚠️ 未检测到签到记录（可能 IP 已被占用）"

print(result)
send("LBB7 签到结果", result)
