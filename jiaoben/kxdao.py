#!/usr/bin/env python3
#修改时间 2025年10月25日14:00（北京时间）  # 优化用户名提取路径
#来自 https://github.com/HeiDaotu/WFRobertQL/blob/main/kxdao.py
# -*- coding: utf-8 -*-
"""科学刀论坛自动签到脚本
功能：多账号签到、显示用户名、自动识别重复签到、异常处理、结果通知
"""

import os
import sys
import time
import random
import re
import requests

# 通知模块导入
try:
    from notify import send
except ImportError:
    print("❌ 未找到通知脚本notify.py，请检查路径！")
    sys.exit()


# ==================== 配置集中管理 ====================
CONFIG = {
    "index_url": "https://www.kxdao.net/",
    "plugin_url": "https://www.kxdao.net/plugin.php?id=dsu_amupper",
    # 增加多个可能的个人空间URL备选
    "space_url_candidates": [
        "https://www.kxdao.net/space.php",
        "https://www.kxdao.net/space.php?do=home",
        "https://www.kxdao.net/home.php",
        "https://www.kxdao.net/u.php",
        "https://www.kxdao.net/member.php?mod=space"
    ],
    "sign_url_template": "https://www.kxdao.net/plugin.php?id=dsu_amupper&ppersubmit=true&formhash={formhash}&infloat=yes&handlekey=dsu_amupper&inajax=1&ajaxtarget=fwin_content_dsu_amupper",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "sleep_range": [2, 5],
    "request_timeout": 15,
    "retry_max_attempts": 3,
    "retry_wait_seconds": 2
}

# 结果匹配关键词
KEYWORDS = {
    "success": {"成功", "获得", "积分", "连续", "奖励"},
    "repeat": {"已签", "重复", "无需", "今日已", "已经"},
    "error": {"失败", "错误", "超时", "无权", "失效", "拒绝"}
}

# 用户名提取正则（扩展更多可能的标签格式）
USERNAME_PATTERNS = [
    r'<strong class="vwmy qq"><a href="space-uid-[\d]+\.html"[^>]+title="访问我的空间">([^<]+)</a></strong>',
    r'<a class="vwmy" href="space-uid-[\d]+\.html"[^>]+>([^<]+)</a>',  # 常见的用户名链接格式
    r'<span class="userinfo">([^<]+)</span>',  # 通用用户信息标签
    r'<div class="username">([^<]+)</div>'   # 用户名容器标签
]


# ==================== 核心功能函数 ====================
def get_username(headers):
    """多URL+多正则匹配提取用户名，增强容错性"""
    try:
        # 尝试所有可能的个人空间URL
        for url in CONFIG["space_url_candidates"]:
            try:
                response = requests.get(url, headers=headers, timeout=CONFIG["request_timeout"])
                if response.status_code != 200:
                    continue  # 跳过非200的URL
                response.encoding = response.apparent_encoding
                
                # 尝试所有可能的用户名正则
                for pattern in USERNAME_PATTERNS:
                    match = re.search(pattern, response.text, re.IGNORECASE)
                    if match:
                        username = match.group(1).strip()
                        print(f"✅ 从{url}提取到用户名：{username}")
                        return username
            except Exception as e:
                print(f"⚠️ 尝试{url}提取用户名失败：{str(e)}")
                continue
        
        # 最后尝试从签到插件页提取
        try:
            response = requests.get(CONFIG["plugin_url"], headers=headers, timeout=CONFIG["request_timeout"])
            response.encoding = response.apparent_encoding
            for pattern in USERNAME_PATTERNS:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    username = match.group(1).strip()
                    print(f"✅ 从签到插件页提取到用户名：{username}")
                    return username
        except Exception as e:
            print(f"⚠️ 从签到插件页提取用户名失败：{str(e)}")
        
        # 所有尝试失败
        return None
    except Exception as e:
        print(f"⚠️ 获取用户名失败：{str(e)}（将使用账号序号）")
        return None


def get_latest_formhash(headers):
    """增强版formhash提取"""
    try:
        for url in [CONFIG["index_url"], CONFIG["plugin_url"]]:
            response = requests.get(url, headers=headers, timeout=CONFIG["request_timeout"])
            response.encoding = response.apparent_encoding
            response.raise_for_status()
            
            patterns = [
                r'formhash=([a-f0-9]{8,16})',
                r'<input type="hidden" name="formhash" value="([a-f0-9]{8,16})"',
                r'data-formhash="([a-f0-9]{8,16})"'
            ]
            for pattern in patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    return match.group(1)
        return None
    except Exception as e:
        print(f"❌ 获取formhash失败：{str(e)}")
        return None


def send_sign_request(sign_url, headers):
    """原生重试机制"""
    for attempt in range(CONFIG["retry_max_attempts"]):
        try:
            response = requests.get(
                sign_url,
                headers=headers,
                timeout=CONFIG["request_timeout"],
                allow_redirects=False
            )
            return response
        except Exception as e:
            if attempt < CONFIG["retry_max_attempts"] - 1:
                print(f"⚠️ 第{attempt+1}次请求失败，{CONFIG['retry_wait_seconds']}秒后重试：{str(e)}")
                time.sleep(CONFIG["retry_wait_seconds"])
            else:
                raise


def parse_sign_result(html_content):
    """解析签到结果"""
    content_lower = html_content.lower()
    if any(kw.lower() in content_lower for kw in KEYWORDS["success"]):
        return "签到成功"
    if any(kw.lower() in content_lower for kw in KEYWORDS["repeat"]):
        return "今日已签到（无需重复操作）"
    if any(kw.lower() in content_lower for kw in KEYWORDS["error"]):
        return "签到失败（可能Cookie失效或无权限）"
    
    patterns = [
        r"errorhandle_dsu_amupper\('([^']*)', {}\);",
        r"showDialog\('([^']*)', 'alert'",
        r"提示信息.*?([^<]+)</div>",
        r"alert_error.*?([^<]+)</"
    ]
    for pattern in patterns:
        match = re.search(pattern, html_content, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return "签到结果未知（页面结构可能已变更）"


def process_single_account(account_idx, cookie):
    """处理单个账号"""
    try:
        delay = random.randint(*CONFIG["sleep_range"])
        print(f"随机延迟{delay}秒...")
        time.sleep(delay)
        
        cookie = cookie.strip()
        if not cookie:
            return f"❌ 第{account_idx}个账号：Cookie为空"
        
        headers = {
            "User-Agent": CONFIG["user_agent"],
            "Cookie": cookie,
            "Referer": CONFIG["index_url"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        
        username = get_username(headers)
        account_name = username if username else f"第{account_idx}个账号"
        print(f"当前账号：{account_name}")
        
        formhash = get_latest_formhash(headers)
        if not formhash:
            return f"❌ {account_name}：无法获取formhash"
        print(f"✅ 获取到formhash：{formhash}")
        
        sign_url = CONFIG["sign_url_template"].format(formhash=formhash)
        print("发送签到请求...")
        response = send_sign_request(sign_url, headers)
        response.raise_for_status()
        
        if response.status_code == 200:
            html_content = response.content.decode('utf-8', errors='ignore')
            result_text = parse_sign_result(html_content)
            return f"{'✅' if '成功' in result_text or '已签' in result_text else '❌'} {account_name}：{result_text}"
        else:
            return f"❌ {account_name}：请求失败（状态码{response.status_code}）"
    
    except Exception as e:
        fallback_name = f"第{account_idx}个账号"
        return f"❌ {account_name if 'account_name' in locals() else fallback_name}：处理异常 - {str(e)}"


# ==================== 主函数 ====================
def main():
    sign_results = []
    cookies_str = os.environ.get("KXDAO_COOKIE", "")
    
    if not cookies_str:
        err_msg = "❌ 未配置KXDAO_COOKIE环境变量"
        print(err_msg)
        sign_results.append(err_msg)
        send("科学刀签到失败", "\n".join(sign_results))
        return
    
    account_idx = 1
    for cookie in cookies_str.split("&"):
        print(f"\n===== 处理第{account_idx}个账号 =====")
        result = process_single_account(account_idx, cookie)
        print(result)
        sign_results.append(result)
        account_idx += 1
    
    print("\n===== 签到结果汇总 =====")
    final_result = "\n".join(sign_results)
    print(final_result)
    # 推送失败处理
    try:
        send("科学刀论坛签到结果", final_result)
    except Exception as e:
        print(f"⚠️ 通知推送失败：{str(e)}（签到结果已正常生成）")


if __name__ == '__main__':
    main()
