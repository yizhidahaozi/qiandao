#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File: mt.py(MT论坛签到-青龙API版)
Author: Mrzqd & 优化版.
Date: 2025/10/19
cron: 30 7 * * *
new Env('MT论坛签到');
功能：多账号签到+青龙API通知+Cookie有效性检测+日志记录
"""
from time import sleep
import requests
import re
import os
import sys
import urllib.parse
import random
import logging
from datetime import datetime
import warnings
# 消除SSL证书验证警告（避免访问MT论坛时的InsecureRequestWarning）
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# -------------------------- 1. 基础配置（环境变量驱动，无需改代码） --------------------------
# User-Agent池：模拟不同设备，降低反爬概率
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36"
]

# 从环境变量读取配置（青龙面板中设置，默认值兜底）
CONFIG = {
    # 签到配置
    "sleep_min": int(os.environ.get("MT_SLEEP_MIN", 10)),  # 账号间最小等待时间（秒）
    "sleep_max": int(os.environ.get("MT_SLEEP_MAX", 30)),  # 账号间最大等待时间（秒）
    "request_timeout": int(os.environ.get("MT_TIMEOUT", 15)),  # 请求超时（秒）
    "retry_count": int(os.environ.get("MT_RETRY", 3)),  # 请求重试次数
    # 青龙API配置（必需！在青龙「系统设置→API设置」中获取）
    "ql_url": os.environ.get("QL_URL", "").rstrip("/"),  # 青龙地址（如http://192.168.1.100:5700）
    "ql_token": os.environ.get("QL_TOKEN", ""),  # 青龙API Token
    # 签到目标配置
    "mt_sign_url": "https://bbs.binmt.cc/plugin.php?id=k_misign:sign",  # MT签到接口
    "mt_profile_url": "https://bbs.binmt.cc/home.php?mod=space"  # MT用户中心（验证Cookie）
}

# -------------------------- 2. 日志初始化（控制台+文件双输出） --------------------------
def init_logger():
    logger = logging.getLogger("MT_Sign_Optimized")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    
    # 控制台日志：简洁格式
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    
    # 文件日志：详细记录（按日期命名，便于追溯）
    log_file = f"mt_sign_log_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(
        os.path.join(os.path.dirname(__file__), log_file),  # 日志存脚本同目录
        encoding="utf-8"
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

logger = init_logger()

# -------------------------- 3. 工具函数（稳定签到核心） --------------------------
def safe_request(url, headers, method="GET", data=None):
    """带重试的安全请求：处理超时、断连，兼容GET/POST"""
    for retry in range(CONFIG["retry_count"]):
        try:
            if method.upper() == "GET":
                resp = requests.get(
                    url, headers=headers, timeout=CONFIG["request_timeout"],
                    verify=False  # MT论坛证书可能不兼容，关闭验证（已忽略警告）
                )
            else:  # POST
                resp = requests.post(
                    url, headers=headers, json=data, timeout=CONFIG["request_timeout"],
                    verify=False
                )
            resp.raise_for_status()  # 触发HTTP错误（4xx/5xx）
            return resp
        except requests.exceptions.Timeout:
            logger.warning(f"请求超时（{retry+1}/{CONFIG['retry_count']}），2秒后重试...")
        except requests.exceptions.ConnectionError:
            logger.warning(f"网络断连（{retry+1}/{CONFIG['retry_count']}），2秒后重试...")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP错误：{e.response.status_code}（{e.response.reason}），停止重试")
            return None
        except Exception as e:
            logger.error(f"未知错误：{str(e)}（{retry+1}/{CONFIG['retry_count']}），2秒后重试...")
        sleep(2)  # 重试间隔
    
    logger.error(f"请求失败（已重试{CONFIG['retry_count']}次）")
    return None

def extract_mt_cookie(raw_cookie):
    """精准提取MT必需Cookie：只保留saltkey和auth，自动URL编码"""
    cookie_dict = {}
    # 拆分Cookie（处理可能的空格、多余字符）
    for item in raw_cookie.strip().split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        # 按第一个=拆分（避免Value含=导致错误）
        key, value = item.split("=", 1)
        # 只保留MT论坛签到必需的两个字段
        if key.strip() == "cQWy_2132_saltkey":
            cookie_dict["cQWy_2132_saltkey"] = value.strip()
        elif key.strip() == "cQWy_2132_auth":
            cookie_dict["cQWy_2132_auth"] = value.strip()
    
    # 验证Cookie完整性
    if len(cookie_dict) < 2:
        logger.error("Cookie不完整：缺少cQWy_2132_saltkey或cQWy_2132_auth字段")
        return ""
    
    # 拼接标准Cookie字符串（Value URL编码，避免特殊字符问题）
    return "; ".join([
        f"{k}={urllib.parse.quote(v)}" 
        for k, v in cookie_dict.items()
    ])

def is_cookie_valid(headers):
    """验证Cookie有效性：访问用户中心，避免无效签到请求"""
    resp = safe_request(CONFIG["mt_profile_url"], headers)
    if not resp:
        logger.warning("Cookie验证请求失败，默认视为无效")
        return False
    # 已登录：页面含“我的帖子”“设置”等关键词；未登录：含“请登录”
    login_marks = ["请登录", "登录账号", "忘记密码"]
    if any(mark in resp.text for mark in login_marks):
        return False
    return True

# -------------------------- 4. 青龙API通知（优化配置提示+重试） --------------------------
def send_ql_notify(title, content):
    """调用青龙API发送通知：优化配置提示，支持重试"""
    # 1. 检查青龙配置完整性
    if not CONFIG["ql_url"] or not CONFIG["ql_token"]:
        logger.error("\n【青龙API配置缺失！请按以下步骤设置】")
        logger.error("1. 新增环境变量 QL_URL：青龙面板地址（如http://192.168.1.100:5700）")
        logger.error("2. 新增环境变量 QL_TOKEN：青龙「系统设置→API设置」中生成的Token")
        logger.error("3. 保存后重新运行脚本\n")
        return False
    
    # 2. 构造青龙通知请求
    notify_api = f"{CONFIG['ql_url']}/api/cron/sendNotify"
    headers = {
        "Authorization": f"Bearer {CONFIG['ql_token']}",
        "Content-Type": "application/json"
    }
    # 适配青龙通知格式：支持Markdown（多数渠道兼容）
    notify_data = {
        "title": title,
        "content": content,
        "to": "",  # 留空=使用青龙默认通知渠道
        "sound": "default"
    }
    
    # 3. 发送请求（1次重试，避免临时网络问题）
    for retry in range(2):
        resp = safe_request(notify_api, headers, method="POST", data=notify_data)
        if not resp:
            if retry == 0:
                logger.warning("青龙通知请求失败，1秒后重试...")
                sleep(1)
                continue
            logger.error("青龙通知发送失败")
            return False
        
        # 解析青龙响应（不同版本响应格式兼容）
        try:
            resp_json = resp.json()
            if resp.status_code == 200 and resp_json.get("code") == 200:
                logger.info("✅ 青龙API通知发送成功")
                return True
            else:
                err_msg = resp_json.get("msg", "未知错误")
                logger.error(f"青龙通知失败：{err_msg}（响应内容：{resp.text}）")
                return False
        except Exception as e:
            logger.error(f"解析青龙响应失败：{str(e)}（响应内容：{resp.text}）")
            return False

# -------------------------- 5. 签到核心逻辑（多账号+结果统计） --------------------------
def load_mt_cookies():
    """加载MT Cookie：支持多账号（&分隔），过滤空值"""
    mt_cookie_str = os.environ.get("MT_COOKIE", "")
    if not mt_cookie_str:
        logger.error("\n【MT_COOKIE未配置！】")
        logger.error("操作步骤：")
        logger.error("1. 登录MT论坛（https://bbs.binmt.cc/）")
        logger.error("2. F12→Application→Cookies→复制 cQWy_2132_saltkey 和 cQWy_2132_auth")
        logger.error("3. 新增环境变量 MT_COOKIE：格式为“saltkey=xxx; auth=yyy”（多账号用&分隔）")
        logger.error("4. 保存后重新运行\n")
        sys.exit(1)
    
    # 拆分多账号Cookie，过滤空字符串
    return [cookie for cookie in mt_cookie_str.split("&") if cookie.strip()]

def get_sign_formhash(headers):
    """获取MT签到必需的formhash：页面正则提取"""
    # 访问签到页面获取formhash
    resp = safe_request(f"{CONFIG['mt_sign_url']}-sign.html", headers)
    if not resp:
        return ""
    
    # 正则匹配formhash（兼容HTML格式差异）
    formhash_pattern = r'<input\s+type="hidden"\s+name="formhash"\s+value="([a-zA-Z0-9]+)"\s*/?>'
    match = re.search(formhash_pattern, resp.text, re.IGNORECASE)
    if not match:
        logger.error("未提取到formhash：可能MT论坛页面结构更新")
        return ""
    return match.group(1)

def do_single_sign(headers, formhash):
    """执行单个账号签到：返回详细结果"""
    # 构造签到请求URL
    sign_url = (
        f"{CONFIG['mt_sign_url']}"
        f"?operation=qiandao&formhash={formhash}&format=empty&inajax=1&ajaxtarget="
    )
    
    resp = safe_request(sign_url, headers)
    if not resp:
        return "签到失败：请求超时/网络错误"
    
    # 解析签到结果（MT论坛返回CDATA格式）
    cdata_pattern = r"<!\[CDATA\[(.*?)\]\]>"
    match = re.search(cdata_pattern, resp.text)
    if not match:
        return f"签到失败：未解析到结果（页面内容：{resp.text[:100]}...）"
    
    result = match.group(1).strip()
    if not result:
        return "签到成功 ✅"
    elif result == "今日已签":
        return "今日已签 🟡"
    else:
        return f"签到异常：{result} ❗"

# -------------------------- 6. 主函数（流程串联） --------------------------
def main():
    logger.info("="*50)
    logger.info("MT论坛签到脚本（优化版）开始执行")
    logger.info("="*50)
    
    # 1. 加载Cookie
    mt_cookies = load_mt_cookies()
    total_accounts = len(mt_cookies)
    logger.info(f"共加载{total_accounts}个账号")
    if total_accounts == 0:
        logger.error("未获取到有效账号Cookie，退出脚本")
        sys.exit(1)
    
    # 2. 遍历账号执行签到
    sign_results = []
    for idx, raw_cookie in enumerate(mt_cookies, 1):
        logger.info(f"\n【处理第{idx}个账号】")
        
        # 2.1 提取有效Cookie
        valid_cookie = extract_mt_cookie(raw_cookie)
        if not valid_cookie:
            err_msg = f"第{idx}个账号：Cookie无效（跳过）"
            logger.error(err_msg)
            sign_results.append(err_msg)
            continue
        
        # 2.2 构造请求头
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Cookie": valid_cookie,
            "Referer": "https://bbs.binmt.cc/",  # 模拟正常访问来源
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        
        # 2.3 验证Cookie有效性
        if not is_cookie_valid(headers):
            err_msg = f"第{idx}个账号：Cookie已过期（需重新获取）"
            logger.error(err_msg)
            sign_results.append(err_msg)
            continue
        
        # 2.4 随机等待（避免账号间请求密集）
        sleep_time = random.randint(CONFIG["sleep_min"], CONFIG["sleep_max"])
        logger.info(f"随机等待{sleep_time}秒后签到...")
        sleep(sleep_time)
        
        # 2.5 获取formhash
        formhash = get_sign_formhash(headers)
        if not formhash:
            err_msg = f"第{idx}个账号：获取formhash失败（跳过）"
            logger.error(err_msg)
            sign_results.append(err_msg)
            continue
        
        # 2.6 执行签到
        sign_result = do_single_sign(headers, formhash)
        logger.info(f"签到结果：{sign_result}")
        sign_results.append(f"第{idx}个账号：{sign_result}")
    
    # 3. 汇总结果并发送通知
    logger.info("\n" + "="*50)
    logger.info("所有账号处理完成，汇总结果：")
    logger.info("="*50)
    
    # 统计各状态数量
    success_cnt = len([r for r in sign_results if "签到成功" in r])
    signed_cnt = len([r for r in sign_results if "今日已签" in r])
    fail_cnt = total_accounts - success_cnt - signed_cnt
    
    # 构造Markdown格式通知内容（清晰易读）
    notify_content = f"""# MT论坛签到汇总报告
**执行时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**总账号数**：{total_accounts} 个

## 状态统计
- ✅ 签到成功：{success_cnt} 个
- 🟡 今日已签：{signed_cnt} 个
- ❌ 签到失败：{fail_cnt} 个（含过期Cookie、网络错误等）

## 详细结果
""" + "\n".join([f"- {r}" for r in sign_results])
    
    # 打印汇总到日志
    for line in notify_content.split("\n"):
        logger.info(line)
    
    # 发送青龙通知
    send_ql_notify("MT论坛签到汇总", notify_content)
    logger.info("\n脚本执行结束")

if __name__ == "__main__":
    main()
