#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron: 15 7 * * *
new Env('恩山无线论坛');
"""

import requests
import re
import os
import time
import random
import urllib3
urllib3.disable_warnings()

try:
    from notify import send
except ImportError:
    def send(a, b): print(b)

# ==================== 环境变量 ====================
# 青龙中添加：ENSHAN_COOKIE
# ==================================================

def main():
    cookie = os.getenv("ENSHAN_COOKIE", "").strip()
    if not cookie:
        msg = "❌ 请配置环境变量 ENSHAN_COOKIE"
        print(msg)
        send("恩山签到", msg)
        return

    print("===== 恩山无线论坛 签到开始 =====")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.right.com.cn/forum/erling_qd-sign_in.html",
        "Cookie": cookie
    }

    session = requests.Session()
    session.headers.update(headers)

    # 获取 formhash
    try:
        resp = session.get("https://www.right.com.cn/forum/erling_qd-sign_in.html", timeout=10)
        formhash = re.search(r'FORMHASH\s*=\s*[\'"]([a-f0-9]+)[\'"]', resp.text)
        if not formhash:
            msg = "❌ Cookie 已失效"
            print(msg)
            send("恩山签到", msg)
            return
        formhash = formhash.group(1)
    except Exception as e:
        msg = f"❌ 获取formhash失败：{str(e)}"
        print(msg)
        send("恩山签到", msg)
        return

    # 签到
    try:
        sign_url = "https://www.right.com.cn/forum/plugin.php?id=erling_qd:action&action=sign"
        res = session.post(sign_url, data={"formhash": formhash}, timeout=10)
        txt = res.text

        if "success" in txt or "已签到" in txt or "签到成功" in txt:
            msg = "✅ 签到成功 / 今日已签到"
        else:
            msg = "ℹ️ 签到完成"

    except Exception as e:
        msg = f"❌ 签到失败：{str(e)}"

    print(msg)
    send("恩山无线论坛签到", msg)

if __name__ == "__main__":
    main()
