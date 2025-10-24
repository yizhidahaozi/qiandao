#!/usr/bin/env python3
# 修改时间2025年10月26日09:00
# -*- coding: utf-8 -*-
"""
File: enshan.py
Env: 恩山论坛签到脚本（通知简化版）
Description: 优化通知内容，仅显示用户易懂的核心结果
"""
import datetime
import os
import sys
import urllib.parse
import random
import time

import requests
from bs4 import BeautifulSoup


# 通知模块（仅显示核心结果，去掉技术细节）
class Notification:
    @staticmethod
    def send(results):
        if not results:
            return False
        notify_content = []
        for res in results:
            # 过滤通知中的技术细节（如“带disabled属性”）
            clean_res = res.replace("且带disabled属性", "").replace("（按钮显示“已签到”）", "")
            if "重复签到" in clean_res:
                notify_content.append(f"🔄 {clean_res}")
            elif "签到成功" in clean_res:
                notify_content.append(f"✅ {clean_res}")
            elif "失败" in clean_res:
                notify_content.append(f"❌ {clean_res}")
            else:
                notify_content.append(f"⚠️ {clean_res}")
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


# 日志模块（保留技术细节用于调试，不影响通知）
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


def check_and_sign(session, cookie, username):
    """核心签到逻辑：识别按钮状态但通知中隐藏技术细节"""
    sign_url = "https://www.right.com.cn/forum/erling_qd-sign_in.html"
    headers = get_headers(referer="https://www.right.com.cn/FORUM/")
    headers['Cookie'] = cookie

    # 1. 访问签到页面
    Logger.info(username, "访问专属签到页面，检查按钮状态...")
    resp = session.get(sign_url, headers=headers, timeout=20)
    time.sleep(random.uniform(1.8, 2.5))
    if resp.status_code != 200:
        return Logger.error(username, f"签到页面访问失败（状态码{resp.status_code}）")

    # 2. 匹配签到按钮
    soup = BeautifulSoup(resp.text, "html.parser")
    sign_btn = soup.find(
        "button",
        id="signin-btn",
        class_=["erqd-checkin-btn", "erqd-checkin-btn2"]
    )
    if not sign_btn:
        return Logger.error(username, "未找到签到按钮，请检查页面结构")

    # 3. 解析按钮状态（日志保留技术细节，通知自动过滤）
    btn_text = sign_btn.get_text(strip=True)
    btn_disabled = sign_btn.has_attr("disabled")

    # 4. 已签到状态（日志详细，通知简化）
    if btn_text == "已签到" and btn_disabled:
        # 日志保留技术细节，便于调试
        Logger.success(username, f"重复签到（按钮显示“已签到”且带disabled属性，无需操作）")
        # 返回给通知的内容去掉技术术语
        return f"[{username}] 重复签到（今日已完成，无需操作）"
    
    # 5. 可签到状态
    elif btn_text == "立即签到" and not btn_disabled:
        Logger.info(username, "检测到可签到状态，准备提交...")
        submit_headers = get_headers(referer=sign_url)
        submit_headers['Cookie'] = cookie
        submit_headers['Content-Type'] = "application/x-www-form-urlencoded"
        resp_submit = session.post(sign_url, headers=submit_headers, data={}, timeout=20)
        time.sleep(random.uniform(1.2, 1.8))

        if "签到成功" in resp_submit.text or "获得恩山币" in resp_submit.text:
            return Logger.success(username, "签到成功（已获得当日奖励）")
        else:
            return Logger.error(username, "提交成功，但未检测到签到成功提示")
    
    # 6. 异常状态
    else:
        return Logger.warning(
            username,
            f"按钮状态异常（文本：{btn_text}），请手动检查"
        )


def sign_in(cookie, account_mark, results):
    """完整签到流程"""
    processed_cookie = ""
    try:
        decoded_cookie = urllib.parse.unquote(cookie.strip())
        for item in decoded_cookie.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                processed_cookie += f"{key}={urllib.parse.quote(value)}; "
        if "rHEX_2132_saltkey" not in processed_cookie or "rHEX_2132_auth" not in processed_cookie:
            results.append(Logger.error(account_mark, "签到失败（缺失关键Cookie字段）"))
            return
    except Exception as e:
        results.append(Logger.error(account_mark, f"签到失败（Cookie解析错误：{str(e)}）"))
        return

    session = requests.Session()
    username = get_username(session, processed_cookie, account_mark)
    results.append(check_and_sign(session, processed_cookie, username))


def main():
    final_results = []
    Logger.info("脚本全局", "=" * 50)
    Logger.info("脚本全局", "恩山论坛签到脚本启动（通知简化版）")
    Logger.info("脚本全局", "=" * 50)

    enshan_cookie = os.environ.get("ENSHAN_COOKIE", "").strip()
    if not enshan_cookie:
        err_msg = Logger.error("脚本全局", "未配置ENSHAN_COOKIE环境变量！请补充后重试")
        final_results.append(err_msg)
        Notification.send(final_results)
        sys.exit(1)

    cookie_list = [c.strip() for c in enshan_cookie.split("&") if c.strip()]
    Logger.info("脚本全局", f"共检测到 {len(cookie_list)} 个有效账号\n")

    for idx, cookie in enumerate(cookie_list, 1):
        sign_in(cookie, f"账号{idx}", final_results)
        Logger.info("脚本全局", "-" * 30)

    Logger.info("脚本全局", "\n所有账号处理完成，结果汇总：")
    for res in final_results:
        print(f"📌 {res}")
    Notification.send(final_results)


if __name__ == '__main__':
    main()
