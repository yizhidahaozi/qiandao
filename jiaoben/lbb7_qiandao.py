#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 只能签到，获取到 Cookie 后关闭网站，不可再去登录网站
# 单账号、单 IP 运行
"""
LBB7 每日签到（单账号稳定版｜自动判断）
cron: 35 8 * * *
"""

import os
import sys
import time
import random
import requests

# ================== 通知 ==================
try:
    from notify import send
except ImportError:
    print("❌ 未找到 notify.py")
    sys.exit(1)

# ================== 配置区 ==================
SIGN_URL = "https://zhh.lbb7.cn/user/ajax_user.php?act=qiandao"
CHECK_URL = "https://zhh.lbb7.cn/user/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/143.0.0.0 Safari/537.36"
# ===========================================

cookie = os.environ.get("LBB7_COOKIE", "").strip()

if not cookie:
    msg = "❌ 未配置 LBB7_COOKIE 环境变量"
    print(msg)
    send("LBB7 签到失败", msg)
    sys.exit(1)

# ======== 关键：完整 AJAX Header ========
headers = {
    "User-Agent": UA,
    "Cookie": cookie,
    "Referer": "https://zhh.lbb7.cn/user/qiandao.php",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

print("📌 开始 LBB7 每日签到")

# 随机延迟，降低风控
sleep_time = random.randint(1, 3)
print(f"⏳ 随机等待 {sleep_time} 秒")
time.sleep(sleep_time)

session = requests.Session()
session.headers.update(headers)


# === 补齐 AJAX 关键头（仅用于签到接口识别）===
session.headers.update({
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
})




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

# ================== 执行签到（自动判断） ==================
try:
    resp = session.get(SIGN_URL, timeout=10)

    try:
        data = resp.json()
    except ValueError:
        raise Exception("返回内容非 JSON，可能触发风控")

    msg_text = data.get("msg", "")

    # ===== 自动判断逻辑 =====
    if data.get("code") == 0:
        msg = f"🎉 签到成功：{msg_text}"

    elif any(k in msg_text for k in ["已签到", "今天", "重复"]):
        msg = f"✅ 今日已签到：{msg_text}"

    else:
        msg = f"⚠️ 签到失败：{msg_text}"

    print(msg)
    send("LBB7 每日签到结果", msg)

except Exception as e:
    msg = f"❌ 请求异常：{e}"
    print(msg)
    send("LBB7 签到异常", msg)

print("✅ 脚本执行完成")
