#!/usr/bin/env python3
#修改时间：2025年10月25日
# const $ = new Env('MT论坛')
# -*- coding: utf-8 -*-


import requests
import re
import os
import sys
import time
import random
import urllib.parse

try:
    from notify import send
except ImportError:
    print("❌ 缺少 notify.py")
    sys.exit(1)

BASE = "https://bbs.binmt.cc"
cookies_env = os.environ.get("MT_COOKIE", "")
results = []

if not cookies_env:
    send("MT论坛签到", "❌ 未配置 MT_COOKIE")
    sys.exit(1)

for idx, raw_cookie in enumerate(cookies_env.split("&"), start=1):

    print(f"\n📌 开始处理第{idx}个账号")
    time.sleep(random.randint(1, 2))

    # -------- Cookie 处理 --------
    raw_cookie = urllib.parse.unquote(raw_cookie)
    cookie = ""
    for kv in raw_cookie.split(";"):
        kv = kv.strip()
        if kv.startswith("cQWy_2132_saltkey=") or kv.startswith("cQWy_2132_auth="):
            k, v = kv.split("=", 1)
            cookie += f"{k}={urllib.parse.quote(v)}; "

    if "saltkey" not in cookie or "auth" not in cookie:
        msg = f"❌ 账号{idx}：Cookie 无效"
        print(msg)
        results.append(msg)
        continue

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": cookie,
        "Referer": BASE + "/"
    }

    # -------- 初始化：用户名 + formhash --------
    try:
        page = requests.get(
            f"{BASE}/plugin.php?id=k_misign:sign",
            headers=headers,
            timeout=15
        )
        page.raise_for_status()

        m_user = re.search(r'class="kmuser".*?<span>(.*?)</span>', page.text, re.S)
        username = m_user.group(1).strip() if m_user else f"账号{idx}"
        print(f"✅ 用户名：{username}")

        m_hash = re.search(r'formhash=([a-f0-9]{8})', page.text)
        if not m_hash:
            msg = f"❌ {username}：未获取到 formhash"
            print(msg)
            results.append(msg)
            continue

        formhash = m_hash.group(1)

    except Exception as e:
        msg = f"❌ 账号{idx}：初始化失败 {e}"
        print(msg)
        results.append(msg)
        continue

    # -------- 执行签到 --------
    sign_url = (
        f"{BASE}/plugin.php"
        f"?id=k_misign:sign"
        f"&operation=qiandao"
        f"&formhash={formhash}"
        f"&format=empty"
    )

    try:
        print(f"📝 {username}：执行签到中...")
        r = requests.get(sign_url, headers=headers, timeout=15)
        r.raise_for_status()

        txt = r.text.strip()

        # ✅ 关键修复点：空内容 = 成功
        if txt == "":
            msg = f"🎊 {username}：签到成功"
        elif "已签" in txt:
            msg = f"📅 {username}：今日已签到"
        elif "登录" in txt:
            msg = f"❌ {username}：Cookie 已失效"
        else:
            clean = re.sub(r'<.*?>', '', txt).strip()
            msg = f"ℹ️ {username}：{clean}"

        print(msg)
        results.append(msg)

    except Exception as e:
        msg = f"❌ {username}：请求异常 {e}"
        print(msg)
        results.append(msg)

# -------- 推送 --------
final = "\n".join(results)
print("\n📋 签到结果汇总：")
print(final)
send("MT论坛自动签到结果", final)
