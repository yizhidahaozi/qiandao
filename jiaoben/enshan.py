#!/usr/bin/env python3
# 修改时间2025年10月26日12:00
# -*- coding: utf-8 -*-
"""
File: enshan.py
Env: 恩山论坛签到脚本（文本优先匹配版）
Description: 优先通过按钮文本判定状态，放宽class/type匹配，确保识别成功
"""
import datetime
import os
import sys
import urllib.parse
import random
import time

import requests
from bs4 import BeautifulSoup


# 通知模块（简洁显示结果）
class Notification:
    @staticmethod
    def send(results):
        if not results:
            return False
        notify_content = []
        for res in results:
            if "重复签到" in res:
                notify_content.append(f"🔄 {res}")
            elif "签到成功" in res:
                notify_content.append(f"✅ {res}")
            elif "未找到" in res or "失败" in res:
                notify_content.append(f"❌ {res}")
            else:
                notify_content.append(f"⚠️ {res}")
        notify_title = f"🎯 恩山论坛签到结果 - {datetime.datetime.now().strftime('%Y-%m-%d')}"
        try:
            from notify import send as notify_send
            notify_send(notify_title, "\n".join(notify_content))
            print(f"\n📤 通知发送成功：{notify_title}")
            return True
        except ImportError:
            print("\n❌ 未找到notify.py，无法发送通知")
        except Exception as e:
            print(f"\n❌ 通知发送失败：{str(e)}")
        return False


# 日志模块（详细记录匹配过程）
class Logger:
    @staticmethod
    def info(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ℹ️ [{username}] {msg}"
        print(log_msg)
        return f"[{username}] {msg}"

    @staticmethod
    def success(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ [{username}] {msg}"
        print(log_msg)
        return f"[{username}] {msg}"

    @staticmethod
    def error(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ❌ [{username}] {msg}"
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
        resp = session.get(user_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            tag = soup.find("a", attrs={"title": "访问我的空间"})
            if tag and tag.text.strip():
                return tag.text.strip()
        Logger.info(account_mark, "未提取到用户名（用账号标识）")
    except Exception as e:
        Logger.error(account_mark, f"获取用户名异常：{str(e)}")
    return account_mark


def text_based_sign(session, cookie, username):
    """核心：优先通过按钮文本判定状态，放宽其他匹配条件"""
    sign_url = "https://www.right.com.cn/forum/erling_qd-sign_in.html"
    headers = get_headers(referer="https://www.right.com.cn/FORUM/")
    headers['Cookie'] = cookie

    # 1. 访问签到页面
    Logger.info(username, "访问专属签到页面，查找按钮...")
    resp = session.get(sign_url, headers=headers, timeout=20)
    time.sleep(random.uniform(1.5, 2.5))
    if resp.status_code != 200:
        return Logger.error(username, f"签到页面访问失败（状态码{resp.status_code}）")

    soup = BeautifulSoup(resp.text, "html.parser")
    # 2. 放宽匹配：仅需id=signin-btn，不强制class和type（解决之前匹配失败问题）
    sign_btn = soup.find("button", id="signin-btn")
    if not sign_btn:
        # 二次尝试：若未找到id，直接搜索含“已签到/立即签到”文本的按钮
        sign_btn = soup.find("button", string=lambda t: t and ("已签到" in t or "立即签到" in t))
        if not sign_btn:
            return Logger.error(username, "未找到签到按钮（未匹配到id或关键文本）")

    # 3. 优先通过按钮文本判定状态（你的核心需求）
    btn_text = sign_btn.get_text(strip=True)
    btn_disabled = sign_btn.has_attr("disabled")  # 辅助判断，不强制

    # 3.1 已签到状态（文本为“已签到”，无论class/type）
    if "已签到" in btn_text:
        Logger.success(username, f"识别到已签到状态（按钮文本：{btn_text}，是否禁用：{btn_disabled}）")
        return Logger.success(username, "重复签到（今日已完成，无需操作）")
    
    # 3.2 可签到状态（文本为“立即签到”）
    elif "立即签到" in btn_text:
        Logger.info(username, f"识别到可签到状态（按钮文本：{btn_text}，是否禁用：{btn_disabled}）")
        # 提交签到请求（使用默认地址，确保动作执行）
        submit_headers = get_headers(referer=sign_url)
        submit_headers['Cookie'] = cookie
        submit_headers['Content-Type'] = "application/x-www-form-urlencoded"
        resp_submit = session.post(sign_url, headers=submit_headers, data={}, timeout=20)
        time.sleep(random.uniform(1.2, 1.8))

        if "签到成功" in resp_submit.text or "获得恩山币" in resp_submit.text:
            return Logger.success(username, "签到成功（已获得当日奖励）")
        else:
            return Logger.error(username, "提交后未检测到成功提示")
    
    # 3.3 未知文本状态
    else:
        return Logger.error(username, f"按钮文本异常（文本：{btn_text}），请手动检查")


def sign_in(cookie, account_mark, results):
    """完整签到流程"""
    processed_cookie = ""
    try:
        # 解析Cookie
        decoded_cookie = urllib.parse.unquote(cookie.strip())
        for item in decoded_cookie.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                processed_cookie += f"{key}={urllib.parse.quote(value)}; "
        # 检查核心Cookie字段
        if "rHEX_2132_saltkey" not in processed_cookie or "rHEX_2132_auth" not in processed_cookie:
            results.append(Logger.error(account_mark, "签到失败（缺失核心Cookie字段）"))
            return
    except Exception as e:
        results.append(Logger.error(account_mark, f"签到失败（Cookie解析错误：{str(e)}）"))
        return

    # 执行签到（文本优先匹配）
    session = requests.Session()
    username = get_username(session, processed_cookie, account_mark)
    results.append(text_based_sign(session, processed_cookie, username))


def main():
    final_results = []
    Logger.info("脚本全局", "=" * 50)
    Logger.info("脚本全局", "恩山论坛签到脚本启动（文本优先匹配版）")
    Logger.info("脚本全局", "=" * 50)

    # 读取Cookie
    enshan_cookie = os.environ.get("ENSHAN_COOKIE", "").strip()
    if not enshan_cookie:
        err_msg = Logger.error("脚本全局", "未配置ENSHAN_COOKIE环境变量！请补充后重试")
        final_results.append(err_msg)
        Notification.send(final_results)
        sys.exit(1)

    # 处理多账号
    cookie_list = [c.strip() for c in enshan_cookie.split("&") if c.strip()]
    Logger.info("脚本全局", f"共检测到 {len(cookie_list)} 个有效账号\n")

    # 逐个执行
    for idx, cookie in enumerate(cookie_list, 1):
        sign_in(cookie, f"账号{idx}", final_results)
        Logger.info("脚本全局", "-" * 30)

    # 汇总结果
    Logger.info("脚本全局", "\n所有账号处理完成，结果汇总：")
    for res in final_results:
        print(f"📌 {res}")
    Notification.send(final_results)


if __name__ == '__main__':
    main()
