#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File: mt.py(MT论坛签到)
Author: Mrzqd
Date: 2023/8/27 08:00
cron: 30 7 * * *
new Env('MT论坛签到');
"""
from time import sleep
import requests
import re
import os
import sys
import urllib.parse
import random

# 关键1：导入多渠道通知脚本的send函数（若通知脚本名不是notify.py，需替换为实际文件名）
try:
    from notify import send  # 从notify.py导入核心通知函数
except ImportError:
    print("❌ 未找到通知脚本notify.py，请检查文件路径或文件名！")
    sys.exit()

# 随机等待时间（秒）
sleep_time = [10, 200]  # 随机等待1-2秒，避免请求过于频繁
# 多账号Cookie（用&分隔，优先从环境变量读取）
cookies = os.environ.get("MT_COOKIE", "")

# 初始化签到结果列表（用于汇总所有账号状态）
sign_results = []

# 1. 检查Cookie是否配置
if not cookies:
    err_msg = "❌ MT_COOKIE环境变量未配置，请先填写Cookie！"
    print(err_msg)
    send("MT论坛签到 - 配置错误", err_msg)  # 发送配置错误通知
    sys.exit()

# 2. 遍历多账号Cookie执行签到
account_count = 1
for cookie in cookies.split("&"):
    if not cookie:  # 跳过空Cookie（如多账号最后一个&导致的空值）
        continue
    
    # 账号处理前置提示
    print(f"\n📌 开始处理第{account_count}个账号")
    sleep_t = random.randint(sleep_time[0], sleep_time[1])
    print(f"⏳ 随机等待{sleep_t}秒，避免触发反爬...")
    sleep(sleep_t)

    # 3. 解析并处理Cookie（提取关键字段cQWy_2132_saltkey和cQWy_2132_auth）
    processed_cookie = ""
    cookie = urllib.parse.unquote(cookie)  # 解码URL编码的Cookie
    for item in cookie.split(";"):
        item = item.strip()
        if not item:
            continue
        key, value = item.split("=", 1)  # 避免value含=导致分割错误
        if "cQWy_2132_saltkey" in key:
            processed_cookie += f"cQWy_2132_saltkey={urllib.parse.quote(value)}; "
        elif "cQWy_2132_auth" in key:
            processed_cookie += f"cQWy_2132_auth={urllib.parse.quote(value)};"

    # 检查Cookie有效性
    if not ("cQWy_2132_saltkey" in processed_cookie and "cQWy_2132_auth" in processed_cookie):
        err_msg = f"❌ 第{account_count}个账号：Cookie无效（缺失关键字段）"
        print(err_msg)
        sign_results.append(err_msg)
        account_count += 1
        continue

    # 4. 配置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': processed_cookie,
        'Referer': 'https://bbs.binmt.cc/'  # 增加Referer，模拟正常访问
    }

    # 5. 获取签到所需的formhash
    formhash = ""
    get_formhash_url = "https://bbs.binmt.cc/k_misign-sign.html"
    try:
        print(f"🔍 第{account_count}个账号：正在获取formhash...")
        resp = requests.get(get_formhash_url, headers=headers, timeout=15)
        resp.raise_for_status()  # 自动抛出HTTP错误（如404、500）
        
        # 正则提取formhash
        match = re.search(r'<input\s+type="hidden"\s+name="formhash"\s+value="([^"]+)" />', resp.text)
        if match:
            formhash = match.group(1)
            print(f"✅ 第{account_count}个账号：formhash获取成功（{formhash[:8]}...）")
        else:
            err_msg = f"❌ 第{account_count}个账号：未找到formhash（页面结构可能变化）"
            print(err_msg)
            sign_results.append(err_msg)
            account_count += 1
            continue
    except Exception as e:
        err_msg = f"❌ 第{account_count}个账号：获取formhash失败（{str(e)}）"
        print(err_msg)
        sign_results.append(err_msg)
        account_count += 1
        continue

    # 6. 执行签到请求
    sign_url = f"https://bbs.binmt.cc/plugin.php?id=k_misign:sign&operation=qiandao&formhash={formhash}&format=empty&inajax=1&ajaxtarget="
    try:
        print(f"📝 第{account_count}个账号：正在执行签到...")
        resp = requests.get(sign_url, headers=headers, timeout=15)
        resp.raise_for_status()

        # 解析签到结果（从CDATA中提取）
        match = re.search(r"<!\[CDATA\[(.*?)\]\]>", resp.text)
        if not match:
            err_msg = f"❓ 第{account_count}个账号：未识别到签到结果（返回内容异常）"
            print(err_msg)
            sign_results.append(err_msg)
        else:
            sign_result = match.group(1).strip()
            if not sign_result:
                msg = f"🎊 第{account_count}个账号：签到成功！"
            elif "今日已签" in sign_result:
                msg = f"📅 第{account_count}个账号：今日已签到（无需重复操作）"
            else:
                msg = f"ℹ️ 第{account_count}个账号：签到结果：{sign_result}"
            print(msg)
            sign_results.append(msg)
    except Exception as e:
        err_msg = f"❌ 第{account_count}个账号：签到失败（{str(e)}）"
        print(err_msg)
        sign_results.append(err_msg)
    finally:
        account_count += 1  # 确保账号计数递增

# 7. 汇总所有账号结果并发送多渠道通知
print(f"\n📋 所有账号签到完成，结果汇总：")
final_content = "\n".join(sign_results)
print(final_content)

# 关键2：调用多渠道通知发送汇总结果
send(
    title="MT论坛自动签到结果",  # 通知标题
    content=final_content       # 通知内容（所有账号签到状态）
)
