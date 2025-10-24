#!/usr/bin/env python3
# 修改时间2025年10月26日11:00
# -*- coding: utf-8 -*-
"""
File: enshan.py
Env: 恩山论坛签到脚本（最终稳定版）
Description: 完全适配按钮属性（submit类型+formAction+disabled），精准签到
"""
import datetime
import os
import sys
import urllib.parse
import random
import time

import requests
from bs4 import BeautifulSoup


# 通知模块（简洁无技术细节）
class Notification:
    @staticmethod
    def send(results):
        if not results:
            return False
        notify_content = []
        for res in results:
            # 仅保留“账号+核心结果”，去掉技术术语
            if "重复签到" in res:
                notify_content.append(f"🔄 {res}")
            elif "签到成功" in res:
                notify_content.append(f"✅ {res}")
            elif "失败" in res:
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


# 日志模块（保留技术细节用于调试）
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
    """生成真实浏览器请求头，匹配页面访问环境"""
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


def precise_sign(session, cookie, username):
    """核心：基于按钮完整属性精准处理（submit类型+formAction+disabled）"""
    base_sign_url = "https://www.right.com.cn/forum/erling_qd-sign_in.html"
    headers = get_headers(referer="https://www.right.com.cn/FORUM/")
    headers['Cookie'] = cookie

    # 1. 访问签到页面，获取按钮完整属性
    Logger.info(username, "访问专属签到页面，读取按钮属性...")
    resp = session.get(base_sign_url, headers=headers, timeout=20)
    time.sleep(random.uniform(1.8, 2.5))
    if resp.status_code != 200:
        return Logger.error(username, f"签到页面访问失败（状态码{resp.status_code}）")

    # 2. 精准定位按钮（匹配id+class+type，避免误判）
    soup = BeautifulSoup(resp.text, "html.parser")
    sign_btn = soup.find(
        "button",
        id="signin-btn",
        class_=["erqd-checkin-btn", "erqd-checkin-btn2"],
        type="submit"  # 新增type匹配，确保是提交按钮
    )
    if not sign_btn:
        return Logger.error(username, "未找到签到按钮（id=signin-btn + class=erqd-checkin-btn/2 + type=submit）")

    # 3. 解析按钮关键状态（匹配你提供的属性）
    btn_text = sign_btn.get_text(strip=True)  # 文本：已签到/立即签到
    btn_disabled = sign_btn.get("disabled")  # 是否禁用：true/""
    btn_form_action = sign_btn.get("formAction", base_sign_url)  # 提交地址

    # 4. 已签到状态（disabled=true/"" + 文本“已签到”）
    if btn_text == "已签到" and btn_disabled is not None:
        Logger.success(username, f"重复签到（按钮：文本={btn_text}，禁用={btn_disabled}，提交地址={btn_form_action}）")
        return Logger.success(username, "重复签到（今日已完成，无需操作）")

    # 5. 可签到状态（文本“立即签到” + 未禁用）
    elif btn_text == "立即签到" and btn_disabled is None:
        Logger.info(username, f"可签到状态（按钮：文本={btn_text}，禁用={btn_disabled}，提交地址={btn_form_action}）")
        # 模拟submit提交（使用按钮自带的formAction地址）
        submit_headers = get_headers(referer=base_sign_url)
        submit_headers['Cookie'] = cookie
        submit_headers['Content-Type'] = "application/x-www-form-urlencoded"
        resp_submit = session.post(btn_form_action, headers=submit_headers, data={}, timeout=20)
        time.sleep(random.uniform(1.2, 1.8))

        # 验证提交结果
        if "签到成功" in resp_submit.text or "获得恩山币" in resp_submit.text:
            return Logger.success(username, "签到成功（已获得当日奖励）")
        else:
            return Logger.error(username, "提交成功，但未检测到签到成功提示")

    # 6. 异常状态（按钮属性不匹配预期）
    else:
        return Logger.error(username, f"按钮状态异常（文本={btn_text}，禁用={btn_disabled}），请手动检查")


def sign_in(cookie, account_mark, results):
    """完整签到流程"""
    processed_cookie = ""
    try:
        # 解析并验证Cookie（保留所有字段）
        decoded_cookie = urllib.parse.unquote(cookie.strip())
        for item in decoded_cookie.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                processed_cookie += f"{key}={urllib.parse.quote(value)}; "
        # 检查核心Cookie字段（确保登录有效）
        if "rHEX_2132_saltkey" not in processed_cookie or "rHEX_2132_auth" not in processed_cookie:
            results.append(Logger.error(account_mark, "签到失败（缺失核心Cookie字段，无法登录）"))
            return
    except Exception as e:
        results.append(Logger.error(account_mark, f"签到失败（Cookie解析错误：{str(e)}）"))
        return

    # 执行签到
    session = requests.Session()
    username = get_username(session, processed_cookie, account_mark)
    results.append(precise_sign(session, processed_cookie, username))


def main():
    final_results = []
    Logger.info("脚本全局", "=" * 50)
    Logger.info("脚本全局", "恩山论坛签到脚本启动（最终稳定版）")
    Logger.info("脚本全局", "=" * 50)

    # 读取Cookie环境变量
    enshan_cookie = os.environ.get("ENSHAN_COOKIE", "").strip()
    if not enshan_cookie:
        err_msg = Logger.error("脚本全局", "未配置ENSHAN_COOKIE环境变量！请补充后重试")
        final_results.append(err_msg)
        Notification.send(final_results)
        sys.exit(1)

    # 处理多账号（过滤空值）
    cookie_list = [c.strip() for c in enshan_cookie.split("&") if c.strip()]
    Logger.info("脚本全局", f"共检测到 {len(cookie_list)} 个有效账号\n")

    # 逐个账号执行签到
    for idx, cookie in enumerate(cookie_list, 1):
        sign_in(cookie, f"账号{idx}", final_results)
        Logger.info("脚本全局", "-" * 30)

    # 汇总结果并发送通知
    Logger.info("脚本全局", "\n所有账号处理完成，结果汇总：")
    for res in final_results:
        print(f"📌 {res}")
    Notification.send(final_results)


if __name__ == '__main__':
    main()
