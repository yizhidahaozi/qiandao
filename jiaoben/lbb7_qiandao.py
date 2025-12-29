#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File: lbb7_qiandao.py
Date: 2025/12/29
cron: 23 8 * * *
new Env('LBB7 每日签到');
"""

import os
import sys
import time
import random
import requests

# 青龙通知
try:
    from notify import send
except ImportError:
    send = None
    print("⚠ 未找到 notify.py，将不发送通知")

# ================= 配置 =================
SIGN_URL = "https://zhh.lbb7.cn/user/ajax_user.php?act=qiandao"
REFERER = "https://zhh.lbb7.cn/user/qiandao.php"
SLEEP_RANGE = (1, 3)

cookies_env = os.getenv("QD_COOKIE", "")
# ========================================

if not cookies_env:
    msg = "❌ QD_COOKIE 环境变量未配置"
    print(msg)
    if send:
        send("LBB7 签到失败", msg)
    sys.exit(1)

cookies_list = [c.strip() for c in cookies_env.split("&") if c.strip()]
results = []

for idx, cookie in enumerate(cookies_list, start=1):
    print(f"\n📌 开始第 {idx} 个账号签到")

    sleep_time = random.randint(*SLEEP_RANGE)
    print(f"⏳ 随机等待 {sleep_time} 秒")
    time.sleep(sleep_time)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": cookie,
        "Referer": REFERER
    }

    try:
        r = requests.get(SIGN_URL, headers=headers, timeout=10)

        # Cookie 失效判断（核心、可靠）
        if "login.php" in r.text:
            msg = f"❌ 账号{idx}：Cookie 已失效"
            print(msg)
            results.append(msg)
            continue

        data = r.json()
    except Exception as e:
        msg = f"❌ 账号{idx}：请求异常（{e}）"
        print(msg)
        results.append(msg)
        continue

    # ===== 结果输出（只信任签到接口本身）=====
    if data.get("code") == 0:
        msg = f"✅ 账号{idx}：签到成功（已到账）"
    else:
        msg = f"📅 账号{idx}：{data.get('msg', '签到失败')}"

    print(msg)
    results.append(msg)

# ================= 汇总 & 通知 =================
final_text = "\n".join(results)

print("\n📋 签到结果汇总：")
print(final_text)

if send:
    send(
        title="LBB7 每日签到结果",
        content=final_text
    )
