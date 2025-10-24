#!/usr/bin/env python3
# 修改时间2025年10月25日17:00
# 源码来自 https://github.com/HeiDaotu/WFRobertQL/blob/main/enshan.py
# -*- coding: utf-8 -*-
"""
File: enshan.py
Author: WFRobert
Date: 2023/9/1 1:09
cron: 0 50 6 * * ?
new Env('恩山论坛模拟登录脚本');
Description: 恩山论坛模拟登录,每日登录获得+1恩山币
Update: 2025/10/25 17:00 - 通知添加表情符号，区分签到状态
"""
import datetime
import os
import sys
import urllib.parse
import random
import time

import requests
from bs4 import BeautifulSoup


# 通知功能模块（添加表情，区分状态）
class Notification:
    @staticmethod
    def load_notify_module():
        try:
            from notify import send as notify_send
            return notify_send
        except ImportError:
            print("❌ 未找到通知脚本notify.py，请检查文件路径！")
            return None

    @staticmethod
    def send(results):
        """通知内容带表情，按状态分类显示"""
        if not results:
            return False
        
        # 格式化通知：每条结果前加对应表情，区分状态
        notify_content = []
        for res in results:
            if "重复签到" in res:
                notify_content.append(f"🔄 {res}")  # 重复签到用“循环”表情
            elif "签到成功" in res and "新" not in res:
                notify_content.append(f"✅ {res}")  # 新签到成功用“对勾”表情
            elif "失败" in res:
                notify_content.append(f"❌ {res}")  # 失败用“叉号”表情
            elif "未知" in res:
                notify_content.append(f"⚠️ {res}")  # 未知状态用“警告”表情
            else:
                notify_content.append(f"ℹ️ {res}")  # 其他信息用“信息”表情
        
        # 通知标题带主题表情，更醒目
        notify_title = f"🎯 恩山论坛签到结果 - {datetime.datetime.now().strftime('%Y-%m-%d')}"
        final_content = "\n".join(notify_content)
        
        try:
            from notify import send as notify_send
            notify_send(notify_title, final_content)
            print(f"\n📤 通知发送成功：{notify_title}")
            return True
        except ImportError:
            print("\n❌ 未找到notify.py，无法发送通知")
        except Exception as e:
            print(f"\n❌ 通知发送失败：{str(e)}")
        return False


# 日志处理模块（保持简洁，与通知表情呼应）
class Logger:
    @staticmethod
    def info(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ℹ️ [{username}] {msg}"
        print(log_msg)
        return f"[{username}] {msg}"

    @staticmethod
    def error(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ❌ [{username}] {msg}"
        print(log_msg)
        return f"[{username}] {msg}"

    @staticmethod
    def success(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ [{username}] {msg}"
        print(log_msg)
        return f"[{username}] {msg}"

    @staticmethod
    def warning(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚠️ [{username}] {msg}"
        print(log_msg)
        return f"[{username}] {msg}"


def get_headers(referer="https://www.right.com.cn/forum/"):
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": referer,
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }


def get_username(session, cookie, account_mark):
    """获取用户名，失败用“账号X”兜底"""
    user_url = "https://www.right.com.cn/FORUM/home.php?mod=spacecp&ac=credit&op=base"
    headers = get_headers()
    headers['Cookie'] = cookie
    try:
        response = session.get(user_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            user_name_tag = soup.find('a', attrs={'title': '访问我的空间'})
            if user_name_tag and user_name_tag.text.strip():
                return user_name_tag.text.strip()
        Logger.info(account_mark, "未从页面提取到用户名（使用账号标识）")
    except Exception as e:
        Logger.error(account_mark, f"获取用户名异常：{str(e)}")
    return account_mark


def execute_sign_in(session, cookie, username):
    """执行签到，返回带状态的结果"""
    sign_url = "https://www.right.com.cn/forum/erling_qd-sign_in.html"
    headers = get_headers(referer="https://www.right.com.cn/FORUM/")
    headers['Cookie'] = cookie

    Logger.info(username, "正在访问专属签到地址...")
    response = session.get(sign_url, headers=headers, timeout=20)
    time.sleep(random.uniform(1.5, 2.5))

    if response.status_code != 200:
        return Logger.error(username, f"签到失败（页面访问失败，状态码{response.status_code}）")
    
    page_text = response.text.replace("\n", "").replace(" ", "")
    if "今日已签到" in page_text:
        return Logger.success(username, "重复签到（今日已完成，无需操作）")
    elif "签到成功" in page_text or "获得恩山币" in page_text:
        return Logger.success(username, "签到成功（已获得当日奖励）")
    elif "请先登录" in page_text or "Cookie过期" in page_text:
        return Logger.error(username, "签到失败（Cookie无效或已过期）")
    else:
        return Logger.warning(username, "签到状态未知（未识别页面提示）")


def sign_in(cookie, account_mark, results):
    """单账号签到流程"""
    processed_cookie = ""
    try:
        # 解析Cookie
        decoded_cookie = urllib.parse.unquote(cookie.strip())
        cookie_items = [item.strip() for item in decoded_cookie.split(";") if item.strip()]
        for item in cookie_items:
            if "=" in item:
                key, value = item.split("=", 1)
                processed_cookie += f"{key.strip()}={urllib.parse.quote(value.strip())}; "
        
        # 检查关键字段
        if "rHEX_2132_saltkey" not in processed_cookie or "rHEX_2132_auth" not in processed_cookie:
            results.append(Logger.error(account_mark, "签到失败（缺失关键Cookie字段）"))
            return
    except Exception as e:
        results.append(Logger.error(account_mark, f"签到失败（Cookie解析错误：{str(e)}）"))
        return

    # 执行签到并记录结果
    session = requests.Session()
    username = get_username(session, processed_cookie, account_mark)
    sign_result = execute_sign_in(session, processed_cookie, username)
    results.append(sign_result)

    # 补充积分提示
    Logger.info(username, "积分记录查询（可能存在同步延迟，以签到提示为准）")


def main():
    final_notify_content = []
    Logger.info("脚本全局", "=" * 50)
    Logger.info("脚本全局", "恩山论坛模拟登录脚本启动（表情通知版）")
    Logger.info("脚本全局", "=" * 50)

    # 读取Cookie
    enshan_cookie = os.environ.get("ENSHAN_COOKIE", "").strip()
    if not enshan_cookie:
        err_msg = Logger.error("脚本全局", "未配置ENSHAN_COOKIE环境变量！请补充后重试")
        final_notify_content.append(err_msg)
        Notification.send(final_notify_content)
        sys.exit(1)

    # 处理多账号
    cookie_list = [c.strip() for c in enshan_cookie.split("&") if c.strip()]
    Logger.info("脚本全局", f"共检测到 {len(cookie_list)} 个有效账号，开始处理...\n")

    # 逐个执行签到
    for idx, cookie in enumerate(cookie_list, 1):
        account_mark = f"账号{idx}"
        sign_in(cookie, account_mark, final_notify_content)
        Logger.info("脚本全局", "-" * 30)

    # 汇总结果并发送通知
    Logger.info("脚本全局", "\n所有账号处理完成，结果汇总：")
    for line in final_notify_content:
        print(f"📌 {line}")

    Notification.send(final_notify_content)


if __name__ == '__main__':
    main()
