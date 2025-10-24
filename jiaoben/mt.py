#!/usr/bin/env python3
# 修改时间2025年10月24日13:55
# 源码来自 https://github.com/HeiDaotu/WFRobertQL/blob/main/enshan.py
# -*- coding: utf-8 -*-
"""
File: enshan.py
Author: WFRobert
Date: 2023/9/1 1:09
cron: 0 50 6 * * ?
new Env('恩山论坛模拟登录脚本');
Description: 恩山论坛模拟登录,每日登录获得+1恩山币
Update: 2025/10/24 13:55 - 整合通知功能，优化错误日志，增加请求超时控制
"""
import datetime
import os
import sys
import urllib.parse

import requests
from bs4 import BeautifulSoup


# -------------------------- 通知功能模块 --------------------------
class Notification:
    @staticmethod
    def load_notify_module():
        """加载外部通知脚本（notify.py），兼容常见通知渠道"""
        try:
            from notify import send as notify_send
            return notify_send
        except ImportError:
            print("❌ 未找到通知脚本notify.py，请确认文件路径正确或补充该文件")
            return None

    @staticmethod
    def send(title, content):
        """发送通知主逻辑，包含异常捕获"""
        notify_func = Notification.load_notify_module()
        if not notify_func:
            return False
        
        try:
            notify_func(title, content)
            print(f"✅ 通知发送成功 | 标题：{title}")
            return True
        except Exception as e:
            print(f"❌ 通知发送失败：{str(e)}")
            return False


# -------------------------- 日志处理模块 --------------------------
class Logger:
    @staticmethod
    def info(msg):
        """信息级日志，带时间戳"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] ℹ️ {msg}"
        print(log_msg)
        return log_msg

    @staticmethod
    def error(msg):
        """错误级日志，带时间戳"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] ❌ {msg}"
        print(log_msg)
        return log_msg


# -------------------------- 核心功能函数 --------------------------
def get_user_info(cookie, result_list):
    """获取用户信息（用户名、积分、用户组）并记录结果"""
    info_url = "https://www.right.com.cn/FORUM/home.php?mod=spacecp&ac=credit&op=base"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.right.com.cn/FORUM/home.php?mod=spacecp&ac=credit&showcredit=1",
        "Cookie": cookie,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        # 15秒超时控制，避免请求卡死
        response = requests.get(info_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")
            # 提取用户信息（容错处理，避免标签不存在导致崩溃）
            user_name_tag = soup.find("a", attrs={"title": "访问我的空间"})
            points_tag = soup.find("a", attrs={"id": "extcreditmenu"})
            user_group_tag = soup.find("a", attrs={"id": "g_upmine"})

            if all([user_name_tag, points_tag, user_group_tag]):
                user_name = user_name_tag.text.strip()
                points = points_tag.text.strip()
                user_group = user_group_tag.text.strip()
                success_msg = Logger.info(f"用户信息获取成功 | 用户名：{user_name} | 积分：{points} | 用户组：{user_group}")
                result_list.append(success_msg)
                return user_name
            else:
                err_msg = Logger.error("用户信息提取失败（页面标签可能已变更）")
                result_list.append(err_msg)
                return None
        else:
            err_msg = Logger.error(f"访问用户信息页失败 | 状态码：{response.status_code}")
            result_list.append(err_msg)
            return None
    except Exception as e:
        err_msg = Logger.error(f"获取用户信息异常：{str(e)}")
        result_list.append(err_msg)
        return None


def simulate_sign_in(account_num, cookie, result_list):
    """模拟登录并验证当日登录状态"""
    # 1. 处理Cookie：筛选关键字段并重新编码
    try:
        decoded_cookie = urllib.parse.unquote(cookie)
        cookie_items = decoded_cookie.split(";")
        processed_cookie = ""

        # 提取恩山论坛登录必需的两个Cookie字段
        for item in cookie_items:
            item = item.strip()
            if not item:
                continue
            key, value = item.split("=", 1)  # 避免value含等号导致分割错误
            if "TWcq_2132_saltkey" in key:
                processed_cookie += f"TWcq_2132_saltkey={urllib.parse.quote(value)}; "
            elif "TWcq_2132_auth" in key:
                processed_cookie += f"TWcq_2132_auth={urllib.parse.quote(value)};"

        # 验证Cookie有效性
        if not ("TWcq_2132_saltkey" in processed_cookie and "TWcq_2132_auth" in processed_cookie):
            err_msg = Logger.error(f"第{account_num}个账号 | Cookie无效（缺失saltkey或auth字段）")
            result_list.append(err_msg)
            return
        Logger.info(f"第{account_num}个账号 | Cookie预处理完成")

    except Exception as e:
        err_msg = Logger.error(f"第{account_num}个账号 | Cookie处理异常：{str(e)}")
        result_list.append(err_msg)
        return

    # 2. 访问积分日志页，验证当日登录状态
    sign_verify_url = "https://www.right.com.cn/forum/home.php?mod=spacecp&ac=credit&op=log&suboperation=creditrulelog"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": processed_cookie,
        "Host": "www.right.com.cn",
        "Referer": "https://www.right.com.cn/FORUM/",
        "Accept-Encoding": "gzip, deflate, br"
    }

    try:
        response = requests.get(sign_verify_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 找到积分历史表格（容错：表格不存在时不崩溃）
            credit_table = soup.find("table", summary="积分获得历史")
            if not credit_table:
                err_msg = Logger.error(f"第{account_num}个账号 | 未找到积分历史表格（页面结构变更）")
                result_list.append(err_msg)
                return

            # 遍历表格行，检查当日"每天登录"记录
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            sign_success = False
            for tr in credit_table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 6:  # 有效记录至少6列（时间、类型、积分等）
                    continue
                # 匹配"每天登录"类型且日期为当天
                if tds[0].text.strip() == "每天登录" and tds[5].text.strip()[:10] == today:
                    sign_success = True
                    break

            if sign_success:
                success_msg = Logger.info(f"第{account_num}个账号 | 当日登录验证成功")
                result_list.append(success_msg)
                # 验证成功后获取用户信息
                get_user_info(processed_cookie, result_list)
            else:
                err_msg = Logger.error(f"第{account_num}个账号 | 当日登录验证失败（未找到登录记录）")
                result_list.append(err_msg)
        else:
            err_msg = Logger.error(f"第{account_num}个账号 | 访问积分日志页失败 | 状态码：{response.status_code}")
            result_list.append(err_msg)
    except Exception as e:
        err_msg = Logger.error(f"第{account_num}个账号 | 登录验证异常：{str(e)}")
        result_list.append(err_msg)


# -------------------------- 主执行流程 --------------------------
def main():
    # 初始化结果列表（用于汇总所有账号状态）
    sign_results = []
    Logger.info("=" * 50)
    Logger.info("恩山论坛模拟登录脚本启动")
    Logger.info("=" * 50)

    # 1. 读取环境变量中的Cookie（多账号用&分隔）
    enshan_cookie = os.environ.get("ENSHAN_COOKIE", "")
    if not enshan_cookie:
        err_msg = Logger.error("未配置ENSHAN_COOKIE环境变量，请补充后重试")
        sign_results.append(err_msg)
        # 发送配置错误通知
        Notification.send("恩山论坛登录 - 配置错误", "\n".join(sign_results))
        sys.exit(1)

    # 2. 拆分多账号Cookie并执行登录
    cookie_list = enshan_cookie.split("&")
    Logger.info(f"共检测到 {len(cookie_list)} 个账号")
    for account_index, cookie in enumerate(cookie_list, 1):
        if not cookie.strip():
            Logger.info(f"跳过空Cookie（第{account_index}个账号）")
            continue
        # 分隔不同账号的日志，便于查看
        sign_results.append(f"\n【第{account_index}个账号处理开始】")
        simulate_sign_in(account_index, cookie, sign_results)
        sign_results.append(f"【第{account_index}个账号处理结束】")

    # 3. 汇总结果并发送通知
    Logger.info("\n" + "=" * 50)
    Logger.info("所有账号处理完成，结果汇总：")
    final_result = "\n".join(sign_results)
    print(final_result)

    # 发送通知（标题带日期，便于区分）
    notify_title = f"恩山论坛登录结果 - {datetime.datetime.now().strftime('%Y-%m-%d')}"
    Notification.send(notify_title, final_result)


if __name__ == "__main__":
    main()
