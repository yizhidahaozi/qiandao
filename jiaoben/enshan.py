#!/usr/bin/env python3
#修改时间：2025年12月25日
# -*- coding: utf-8 -*-

"""
cron: 15 7 * * *
new Env('恩山无线论坛签到');
"""
from time import sleep
import requests
import re
import os
import sys
import urllib.parse
import random
import urllib3

# 禁用https警告
urllib3.disable_warnings()

# 导入多渠道通知脚本的send函数
try:
    from notify import send
except ImportError:
    print("❌ 未找到通知脚本notify.py，请检查文件路径或文件名！")
    sys.exit()

# 随机等待时间（秒）
sleep_time = [1, 3]
# 多账号Cookie（用&分隔，优先从环境变量读取）
cookies = os.environ.get("ENSHAN_COOKIE", "")

# 初始化签到结果列表
sign_results = []

# 检查Cookie是否配置
if not cookies:
    err_msg = "❌ ENSHAN_COOKIE环境变量未配置，请先填写Cookie！"
    print(err_msg)
    send("恩山无线论坛签到 - 配置错误", err_msg)
    sys.exit()

# 遍历多账号Cookie执行签到
account_count = 1
for cookie in cookies.split("&"):
    if not cookie:
        continue
    
    # 账号处理前置提示
    print(f"\n📌 开始处理第{account_count}个账号")
    sleep_t = random.randint(sleep_time[0], sleep_time[1])
    print(f"⏳ 随机等待{sleep_t}秒，避免触发反爬...")
    sleep(sleep_t)

    # 处理Cookie（解码+格式化）
    processed_cookie = urllib.parse.unquote(cookie).strip()
    if not processed_cookie:
        err_msg = f"❌ 第{account_count}个账号：Cookie为空"
        print(err_msg)
        sign_results.append(err_msg)
        account_count += 1
        continue

    # 配置请求头（模拟真实浏览器）
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Cookie': processed_cookie,
        'Referer': 'https://www.right.com.cn/forum/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive'
    }

    # 创建会话（保持Cookie状态）
    session = requests.Session()
    session.headers.update(headers)

    # ---------------------- 1. 获取formhash ----------------------
    formhash = ""
    get_formhash_url = "https://www.right.com.cn/forum/forum.php"
    try:
        print(f"🔍 第{account_count}个账号：正在获取formhash...")
        resp = session.get(get_formhash_url, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        
        # 多规则提取formhash
        match = re.search(r'name=["\']formhash["\']\s+value=["\']([0-9a-fA-F]+)["\']', resp.text)
        if not match:
            match = re.search(r"formhash\s*[:=]\s*['\"]([0-9a-fA-F]+)['\"]", resp.text)
        if not match:
            match = re.search(r'name=["\']formhash["\']\s+value=["\']([^"\']+)["\']', resp.text)
        
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

    # ---------------------- 2. 提取用户名（跳过521错误，不影响核心） ----------------------
    username = f"账号{account_count}"  # 默认用编号
    try:
        print(f"🔍 第{account_count}个账号：正在获取用户名...")
        # 访问用户资产页提取用户名
        user_info_url = "https://www.right.com.cn/forum/home.php?mod=spacecp&ac=credit&showcredit=1"
        user_resp = session.get(user_info_url, timeout=20, allow_redirects=True)
        user_resp.raise_for_status()
        
        # 匹配用户名（多规则）
        user_match = re.search(r'<a[^>]+class="xi2"[^>]*>(.*?)</a>', user_resp.text)
        if not user_match:
            user_match = re.search(r'欢迎您：\s*<a[^>]+>(.*?)</a>', user_resp.text)
        if user_match:
            username_raw = user_match.group(1).strip()
            username = re.sub(r'<.*?>', '', username_raw).strip()  # 清理标签
            print(f"✅ 用户名获取成功：{username}")
        else:
            print(f"⚠️ 未识别到用户名，将使用默认编号")
    except Exception as e:
        # 捕获521错误，仅提示不终止
        if "521" in str(e):
            print(f"⚠️ 用户名获取受限（网站风控），将使用默认编号")
        else:
            print(f"⚠️ 获取用户名失败（{str(e)}），将使用默认编号")

    # ---------------------- 3. 执行签到 ----------------------
    sign_url = "https://www.right.com.cn/forum/plugin.php?id=erling_qd:action&action=sign"
    try:
        print(f"📝 {username}：正在执行签到...")
        payload = {"formhash": formhash}
        resp = session.post(sign_url, data=payload, timeout=20)
        resp.raise_for_status()

        # 解析签到结果
        try:
            data = resp.json()
            if data.get("success"):
                continuous_days = data.get("continuous_days", "未知")
                msg = f"🎊 {username}：签到成功！（连续签到{continuous_days}天）"
            else:
                msg = f"ℹ️ {username}：签到结果：{data.get('message', '签到失败')}"
        except ValueError:
            # JSON解析失败时返回状态码
            msg = f"❓ {username}：签到异常（状态码{resp.status_code}）"
        
        print(msg)
        sign_results.append(msg)

        # ---------------------- 4. 获取积分（兼容521风控，友好提示） ----------------------
        point = "未获取到"
        try:
            print(f"🔍 {username}：正在获取积分...")
            # 多URL重试获取积分
            point_urls = [
                "https://www.right.com.cn/forum/home.php?mod=spacecp&ac=credit&showcredit=1",
                "https://www.right.com.cn/forum/space-uid-1.html",
                "https://www.right.com.cn/forum/forum.php"
            ]
            point_patterns = [
                r"<em>积分[:：]\s*</em>(.*?)<span",
                r"积分[:：]\s*(\d+)",
                r"积分</a>[:：]\s*(\d+)",
                r'<li class="credit l_f">.*?积分[:：]\s*(\d+)'
            ]
            
            for url in point_urls:
                if point == "未获取到":
                    point_resp = session.get(url, timeout=20, allow_redirects=True)
                    point_resp.raise_for_status()
                    html = point_resp.text.lower()
                    for pattern in point_patterns:
                        match = re.findall(pattern, html)
                        if match:
                            point = match[0].strip()
                            break
                else:
                    break
            
            if point != "未获取到":
                point_msg = f"📊 {username}：当前积分：{point}"
            else:
                point_msg = f"ℹ️ {username}：积分暂未获取到（非签到失败）"
            print(point_msg)
            # 仅在积分获取成功时添加到通知，避免冗余
            if point != "未获取到":
                sign_results.append(point_msg)
        except Exception as e:
            # 捕获521错误，友好提示（不加入通知列表，避免干扰）
            if "521" in str(e):
                point_msg = f"ℹ️ {username}：积分获取受限（网站风控，签到已成功）"
            else:
                point_msg = f"⚠️ {username}：获取积分失败（{str(e)}）"
            print(point_msg)

    except Exception as e:
        err_msg = f"❌ {username}：签到失败（{str(e)}）"
        print(err_msg)
        sign_results.append(err_msg)
    finally:
        account_count += 1

# ---------------------- 汇总结果并发送通知 ----------------------
print(f"\n📋 所有账号签到完成，结果汇总：")
final_content = "\n".join(sign_results)
print(final_content)

# 发送通知
send(
    title="恩山无线论坛自动签到结果",
    content=final_content
)
