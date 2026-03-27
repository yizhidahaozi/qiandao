#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron: 01 7 * * *
new Env('MT论坛签到');
"""

import requests
import re
import os
import sys
import time
import random
import urllib.parse

# 通知模块导入
try:
    from notify import send
except ImportError:
    print("❌ 缺少 notify.py 文件，无法发送通知")
    sys.exit(1)

# 基础配置
BASE_URL = "https://bbs.binmt.cc"
COOKIE_ENV = os.environ.get("MT_COOKIE", "")
RESULT_LIST = []

# 无Cookie直接退出
if not COOKIE_ENV:
    send("MT论坛签到", "❌ 未配置环境变量 MT_COOKIE")
    sys.exit(1)

# 遍历所有账号
for index, cookie_str in enumerate(COOKIE_ENV.split("&"), 1):
    print(f"\n====== 开始处理第 {index} 个账号 ======")
    time.sleep(random.uniform(1, 3))  # 随机延时防检测
    
    # 1. 清洗并提取有效Cookie（只保留saltkey和auth）
    cookie_str = urllib.parse.unquote(cookie_str).strip()
    valid_cookie = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if item.startswith(("cQWy_2132_saltkey=", "cQWy_2132_auth=")):
            valid_cookie.append(item)
    
    cookie = "; ".join(valid_cookie)
    if not valid_cookie:
        err_msg = f"❌ 账号{index}：Cookie 格式无效"
        print(err_msg)
        RESULT_LIST.append(err_msg)
        continue

    # 请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": cookie,
        "Referer": f"{BASE_URL}/",
        "Accept": "text/html,application/xhtml+xml,*/*"
    }

    try:
        # 2. 获取页面信息 + formhash
        resp = requests.get(f"{BASE_URL}/plugin.php?id=k_misign:sign", headers=headers, timeout=20)
        resp.raise_for_status()
        html = resp.text

        # 提取用户名
        user_match = re.search(r'class="kmuser".*?<span>(.*?)</span>', html, re.S)
        username = user_match.group(1).strip() if user_match else f"账号{index}"

        # 提取formhash
        hash_match = re.search(r'formhash=([a-f0-9]{8})', html)
        if not hash_match:
            err_msg = f"❌ {username}：获取 formhash 失败"
            print(err_msg)
            RESULT_LIST.append(err_msg)
            continue
        formhash = hash_match.group(1)

        # 3. 执行签到
        sign_url = f"{BASE_URL}/plugin.php?id=k_misign:sign&operation=qiandao&formhash={formhash}&format=empty"
        sign_resp = requests.get(sign_url, headers=headers, timeout=20)
        sign_resp.raise_for_status()
        res_text = sign_resp.text.strip()

        # 4. 签到结果判断
        if res_text == "":
            msg = f"✅ {username}：签到成功"
        elif "今日已签" in res_text or "已签到" in res_text:
            msg = f"ℹ️ {username}：今日已签到"
        elif "登录" in res_text or "失效" in res_text:
            msg = f"❌ {username}：Cookie 已失效，请重新获取"
        else:
            # 清理HTML标签，纯文本展示
            res_text = re.sub(r'<[^>]+>', '', res_text).strip()
            msg = f"ℹ️ {username}：{res_text}"

        print(msg)
        RESULT_LIST.append(msg)

    except requests.exceptions.RequestException as e:
        err_msg = f"❌ 账号{index}：网络请求失败 ({str(e)[:30]})"
        print(err_msg)
        RESULT_LIST.append(err_msg)
    except Exception as e:
        err_msg = f"❌ 账号{index}：未知错误 ({str(e)[:30]})"
        print(err_msg)
        RESULT_LIST.append(err_msg)

# 结果汇总推送
final_result = "\n".join(RESULT_LIST)
print("\n" + "="*30)
print("📊 MT论坛签到结果汇总")
print("="*30)
print(final_result)
send("MT论坛自动签到", final_result)
