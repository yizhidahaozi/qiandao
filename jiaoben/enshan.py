#!/usr/bin/env python3
# 修改时间2025年10月25日
# -*- coding: utf-8 -*-
"""
File: enshan_final_sign.py
Env: 恩山论坛签到脚本（通用表情版）
Description: 通用符号优化+签到成功置顶+全环节提示增强
Dependencies: requests, beautifulsoup4
"""
import datetime
import os
import sys
import re
import random
import time

import requests
from bs4 import BeautifulSoup


# 通知模块（通用符号优化+签到成功置顶）
class Notification:
    @staticmethod
    def send(results, user_points_info=None):
        if not results:
            return False
        notify_content = []
        # 分类处理结果：签到成功→重复签到→其他
        success_items = []
        repeat_items = []
        other_items = []
        for res in results:
            if res and ("签到成功" in res or "✅" in res):
                success_items.append(f"✅ {res}")
            elif res and ("重复签到" in res or "🔄" in res):
                repeat_items.append(f"🔄 {res}")
            else:
                other_items.append(res) if res else None
        
        # 拼接内容：签到成功→重复签到→积分信息→其他
        if success_items:
            notify_content.extend(success_items)
            notify_content.append("")  # 空行分隔
        
        if repeat_items:
            notify_content.extend(repeat_items)
            notify_content.append("")  # 空行分隔
        
        # 为积分信息添加通用符号
        if user_points_info and all(key in user_points_info for key in ["today", "continuous", "total"]):
            notify_content.append("📊 账号积分与签到天数：")
            notify_content.append(f"   💰 今日积分：{user_points_info['today']}")
            notify_content.append(f"   📅 连续签到：{user_points_info['continuous']} 天")
            notify_content.append(f"   🧮 总签到天数：{user_points_info['total']} 天")
            notify_content.append("")  # 空行分隔
        
        if other_items:
            notify_content.extend(other_items)
        
        # 固定通知标题
        notify_title = f"🎯 恩山论坛签到结果"
        notify_body = "\n".join(notify_content)
        print(f"\n【签到结果汇总】\n标题：{notify_title}\n内容：\n{notify_body}")
        
        # 第三方通知
        try:
            from notify import send as notify_send
            notify_send(notify_title, notify_body)
            print(f"\n📤 第三方通知发送成功")
            return True
        except ImportError:
            print(f"\nℹ️ 未找到notify.py，跳过第三方通知")
        except Exception as e:
            print(f"\n❌ 第三方通知发送失败：{str(e)}")
        return True


# 日志模块（通用符号增强）
class Logger:
    @staticmethod
    def info(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ℹ️ [{username}] {msg}"
        print(log_msg)
        return f"ℹ️ [{username}] {msg}"

    @staticmethod
    def success(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ [{username}] {msg}"
        print(log_msg)
        return f"✅ [{username}] {msg}"

    @staticmethod
    def error(username, msg):
        log_msg = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ❌ [{username}] {msg}"
        print(log_msg)
        return f"❌ [{username}] {msg}"


def get_headers(referer="https://www.right.com.cn/forum/"):
    """生成随机UA"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": referer,
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }


def get_username(session, cookie, account_mark):
    """获取用户名（带重试）"""
    user_url = "https://www.right.com.cn/FORUM/home.php?mod=spacecp&ac=credit&op=base"
    headers = get_headers()
    headers['Cookie'] = cookie
    retry_count = 2

    for i in range(retry_count + 1):
        try:
            resp = session.get(user_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                user_tag = soup.find("a", attrs={"title": "访问我的空间"})
                if user_tag and user_tag.text.strip():
                    return user_tag.text.strip()
            if i < retry_count:
                Logger.info(account_mark, f"用户名获取失败，{retry_count - i}次重试中...")
                time.sleep(random.uniform(1, 2))
        except Exception as e:
            if i < retry_count:
                Logger.error(account_mark, f"用户名获取异常（{str(e)}），{retry_count - i}次重试中...")
                time.sleep(random.uniform(1, 2))
            else:
                Logger.error(account_mark, f"用户名获取异常：{str(e)}")
    
    Logger.info(account_mark, "未提取到用户名，使用账号标识")
    return account_mark


def get_user_points_info(soup, username):
    """提取积分与签到天数（通用符号版）"""
    points_info = {"today": "未知", "continuous": "未知", "total": "未知"}
    points_container = soup.find("div", class_="erqd-points-container")
    if not points_container:
        Logger.info(username, "未找到积分容器，跳过信息提取")
        return points_info
    
    point_items = points_container.find_all("div", class_="erqd-point-item")
    for item in point_items:
        item_text = item.get_text(strip=True)
        if "今日积分" in item_text:
            today_point = item.find("span", class_="erqd-current-point")
            points_info["today"] = today_point.get_text(strip=True) if today_point else "未知"
        elif "连续签到" in item_text:
            continuous_day = item.find("span", class_="erqd-continuous-days")
            points_info["continuous"] = continuous_day.get_text(strip=True) if continuous_day else "未知"
        elif "总签到天数" in item_text:
            total_day = item.find("span", class_="erqd-total-days")
            points_info["total"] = total_day.get_text(strip=True) if total_day else "未知"
    
    Logger.info(username, f"提取到积分信息：💰今日{points_info['today']}分，📅连续{points_info['continuous']}天，🧮总计{points_info['total']}天")
    return points_info


def core_sign_logic(session, cookie, username):
    """核心签到逻辑"""
    sign_page_url = "https://www.right.com.cn/forum/erling_qd-sign_in.html"
    sign_api_url = "https://www.right.com.cn/forum/plugin.php?id=erling_qd:action&action=sign"
    user_points_info = {"today": "未知", "continuous": "未知", "total": "未知"}

    headers = get_headers(referer="https://www.right.com.cn/FORUM/")
    headers['Cookie'] = cookie
    retry_count = 2

    for i in range(retry_count + 1):
        try:
            Logger.info(username, f"访问签到页（{i + 1}/{retry_count + 1}次）")
            resp = session.get(sign_page_url, headers=headers, timeout=20)
            time.sleep(random.uniform(1.5, 2.5))
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                user_points_info = get_user_points_info(soup, username)
                break
            if i < retry_count:
                Logger.info(username, f"页面访问失败（{resp.status_code}），{retry_count - i}次重试中...")
                time.sleep(random.uniform(2, 3))
        except Exception as e:
            if i < retry_count:
                Logger.error(username, f"页面访问异常（{str(e)}），{retry_count - i}次重试中...")
                time.sleep(random.uniform(2, 3))
            else:
                return Logger.error(username, f"页面访问异常：{str(e)}"), user_points_info
    else:
        return Logger.error(username, f"页面访问失败（最终状态码{resp.status_code}）"), user_points_info

    # 提取formhash
    formhash_match = re.search(r"var FORMHASH = '(\w+)';", resp.text)
    if not formhash_match:
        return Logger.error(username, "未找到formhash参数"), user_points_info
    formhash = formhash_match.group(1)
    Logger.info(username, f"成功提取formhash：{formhash}")

    # 检查按钮状态
    sign_btn = soup.find("button", id="signin-btn", class_="erqd-checkin-btn")
    if not sign_btn:
        return Logger.error(username, "未找到签到按钮"), user_points_info
    
    btn_text = sign_btn.get_text(strip=True)
    Logger.info(username, f"当前按钮状态：{btn_text}")

    if btn_text != "立即签到":
        success_msg = Logger.success(username, f"识别到已签到状态（按钮文本：{btn_text}）")
        return Logger.success(username, "重复签到（今日已完成）"), user_points_info

    # 发送签到请求
    Logger.info(username, "发送签到请求")
    api_headers = get_headers(referer=sign_page_url)
    api_headers['Cookie'] = cookie
    api_headers['Content-Type'] = "application/x-www-form-urlencoded; charset=UTF-8"
    api_headers['X-Requested-With'] = "XMLHttpRequest"
    post_data = {"formhash": formhash}

    try:
        resp_api = session.post(sign_api_url, headers=api_headers, data=post_data, timeout=20)
        time.sleep(random.uniform(1.2, 1.8))
    except Exception as e:
        return Logger.error(username, f"签到请求异常：{str(e)}"), user_points_info

    # 验证结果
    try:
        api_result = resp_api.json()
        Logger.info(username, f"签到接口返回：{api_result}")

        if resp_api.status_code == 200 and api_result.get("success"):
            Logger.info(username, "签到成功，获取最新积分信息...")
            resp_update = session.get(sign_page_url, headers=headers, timeout=15)
            soup_update = BeautifulSoup(resp_update.text, "html.parser")
            user_points_info = get_user_points_info(soup_update, username)
            return Logger.success(username, f"签到成功（{api_result.get('message', '获得奖励')}）"), user_points_info
        else:
            error_msg = api_result.get("message", "未知错误")
            return Logger.error(username, f"签到失败（{error_msg}）"), user_points_info
    except ValueError:
        return Logger.error(username, f"签到失败（非JSON返回，状态码{resp_api.status_code}）"), user_points_info


def single_account_sign(cookie, account_idx, results):
    """单账号签到流程"""
    account_mark = f"账号{account_idx}"
    processed_cookie = cookie.strip()

    core_fields = ["rHEX_2132_saltkey", "rHEX_2132_auth"]
    if not all(field in processed_cookie for field in core_fields):
        missing = [f for f in core_fields if f not in processed_cookie]
        results.append(Logger.error(account_mark, f"Cookie无效（缺失：{', '.join(missing)}）"))
        return None
    
    session = requests.Session()
    session.headers.update(get_headers())
    username = get_username(session, processed_cookie, account_mark)
    sign_result, points_info = core_sign_logic(session, processed_cookie, username)
    results.append(sign_result)
    return points_info


def main():
    final_results = []
    final_points_info = None
    Logger.info("全局", "=" * 60)
    Logger.info("全局", "恩山论坛签到脚本启动")
    Logger.info("全局", f"启动时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    Logger.info("全局", "=" * 60)

    enshan_cookie = os.environ.get("ENSHAN_COOKIE", "").strip()
    if not enshan_cookie:
        err_msg = Logger.error("全局", "未配置ENSHAN_COOKIE环境变量！")
        final_results.append(err_msg)
        Notification.send(final_results)
        sys.exit(1)

    cookie_list = []
    for c in enshan_cookie.split("&"):
        c = c.strip()
        if c and c not in cookie_list:
            cookie_list.append(c)
    Logger.info("全局", f"共检测到 {len(cookie_list)} 个有效账号\n")

    for idx, cookie in enumerate(cookie_list, 1):
        Logger.info("全局", f"=== 开始处理【账号{idx}】===")
        if len(cookie_list) == 1:
            final_points_info = single_account_sign(cookie, idx, final_results)
        else:
            single_points = single_account_sign(cookie, idx, final_results)
            if idx == 1:
                final_points_info = [single_points]
            else:
                final_points_info.append(single_points)
        
        if idx < len(cookie_list):
            delay = random.uniform(3, 5)
            Logger.info("全局", f"账号间延迟 {delay:.1f} 秒...\n")
            time.sleep(delay)

    Logger.info("全局", "\n" + "=" * 60)
    Notification.send(final_results, final_points_info)
    Logger.info("全局", "脚本执行完毕")


if __name__ == '__main__':
    main()
