#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron: 15 7 * * *
new Env('恩山无线论坛_二合一版');
"""

import requests
import re
import os
import urllib3
urllib3.disable_warnings()

try:
    from notify import send
except ImportError:
    def send(a, b):
        print(b)

# 登录获取 session（账号密码方式）
def login(username, password):
    session = requests.Session()
    session.verify = False
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Referer": "https://www.right.com.cn/forum/",
        "Host": "www.right.com.cn"
    }
    try:
        resp = session.get("https://www.right.com.cn/forum/member.php?mod=logging&action=login", timeout=15)
        formhash = re.search(r'formhash" value="([a-f0-9]+)"', resp.text).group(1)
    except Exception as e:
        return None, f"获取登录formhash失败: {e}"

    login_data = {
        "formhash": formhash,
        "referer": "https://www.right.com.cn/forum/",
        "loginfield": "username",
        "username": username,
        "password": password,
        "questionid": "0",
        "answer": "",
        "loginsubmit": "true"
    }

    try:
        resp = session.post(
            "https://www.right.com.cn/forum/member.php?mod=logging&action=login&loginsubmit=yes",
            data=login_data,
            timeout=15
        )
        if "logout" in resp.text or username in resp.text or "我的" in resp.text:
            return session, "登录成功"
        else:
            return None, "账号或密码错误"
    except Exception as e:
        return None, f"登录异常: {e}"

# 签到逻辑
def sign_in(session):
    try:
        resp = session.get("https://www.right.com.cn/forum/erling_qd-sign_in.html", timeout=15)
        html = resp.text

        hash_match = re.search(r'FORMHASH\s*=\s*[\'"]([a-f0-9]+)[\'"]', html)
        if not hash_match:
            hash_match = re.search(r'formhash\s*=\s*[\'"]([a-f0-9]+)[\'"]', html)
        if not hash_match:
            return "Cookie/登录已失效，请更新"

        formhash = hash_match.group(1)
        sign_url = "https://www.right.com.cn/forum/plugin.php?id=erling_qd:action&action=sign"
        res = session.post(sign_url, data={"formhash": formhash}, timeout=15)
        txt = res.text

        if '"success":true' in txt or "success" in txt:
            return "✅ 签到成功"
        elif "已签到" in txt or "今天已经签到" in txt:
            return "✅ 今日已签到"
        else:
            return f"ℹ️ 签到返回：{txt[:100]}"
    except Exception as e:
        return f"❌ 签到失败: {str(e)}"

def main():
    print("===== 恩山无线论坛 二合一签到 =====")
    cookie = os.getenv("ENSHAN_COOKIE", "").strip()
    username = os.getenv("ENSHAN_USER", "").strip()
    password = os.getenv("ENSHAN_PWD", "").strip()

    session = requests.Session()
    session.verify = False
    session.timeout = 20
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Referer": "https://www.right.com.cn/forum/erling_qd-sign_in.html",
        "Host": "www.right.com.cn"
    }

    # 优先使用 Cookie
    if cookie:
        print("ℹ️ 检测到 Cookie，使用 Cookie 模式")
        session.headers["Cookie"] = cookie
        msg = sign_in(session)
    # 没有 Cookie 则使用账号密码
    elif username and password:
        print("ℹ️ 未检测到 Cookie，使用账号密码登录")
        session, login_msg = login(username, password)
        print(login_msg)
        if not session:
            send("恩山签到", login_msg)
            return
        msg = sign_in(session)
    else:
        msg = "❌ 请配置 ENSHAN_COOKIE 或 ENSHAN_USER+ENSHAN_PWD"
        print(msg)
        send("恩山签到", msg)
        return

    print(msg)
    send("恩山无线论坛签到", msg)

if __name__ == "__main__":
    main()
