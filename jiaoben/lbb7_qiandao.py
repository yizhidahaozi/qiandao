#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#只能签到，获取到COOK后关闭网站，不可再去登录网站，否则cook会有变动，简单的说就是2选一。
#只能单一账号运行，一个账号只能在一个IP运行。
"""
LBB7 每日签到（单账号稳定版）
cron: 35 8 * * *
"""

import os
import sys
import time
import random
import requests

# 通知
try:
    from notify import send
except ImportError:
    print("❌ 未找到 notify.py")
    sys.exit(1)

# ================== 配置区 ==================
SIGN_URL = "https://zhh.lbb7.cn/user/ajax_user.php?act=qiandao"
CHECK_URL = "https://zhh.lbb7.cn/user/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
# ============================================

cookie = os.environ.get("LBB7_COOKIE", "").strip()

if not cookie:
    msg = "❌ 未配置 LBB7_COOKIE 环境变量"
    print(msg)
    send("LBB7 签到失败", msg)
    sys.exit(1)

headers = {
    "User-Agent": UA,
    "Cookie": cookie,
    "Referer": "https://zhh.lbb7.cn/user/qiandao.php"
}

print("📌 开始 LBB7 每日签到")

# 随机延迟，避免风控
sleep_time = random.randint(1, 3)
print(f"⏳ 随机等待 {sleep_time} 秒")
time.sleep(sleep_time)

session = requests.Session()
session.headers.update(headers)

# ================== Cookie 校验 ==================
try:
    check = session.get(CHECK_URL, timeout=10)
    if "login.php" in check.url or "用户登录" in check.text:
        msg = "❌ Cookie 已失效，请重新登录并更新 Cookie"
        print(msg)
        send("LBB7 签到失败", msg)
        sys.exit(1)
except Exception as e:
    msg = f"❌ Cookie 校验失败：{e}"
    print(msg)
    send("LBB7 签到异常", msg)
    sys.exit(1)

# ================== 执行签到 ==================
try:
    resp = session.get(SIGN_URL, timeout=10)
    data = resp.json()

    if data.get("code") == 0:
        msg = f"🎉 签到成功：{data.get('msg')}"
    else:
        msg = f"📅 {data.get('msg')}"

    print(msg)
    send("LBB7 每日签到结果", msg)

except Exception as e:
    msg = f"❌ 请求异常：{e}"
    print(msg)
    send("LBB7 签到异常", msg)

print("✅ 脚本执行完成")
