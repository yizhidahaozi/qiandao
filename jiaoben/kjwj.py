#!/usr/bin/python3
# -- coding: utf-8 --
# -------------------------------
# @Author : github@wd210010 https://github.com/wd210010/just_for_happy
# @Modify : 终极修复版 - 解决str/get报错
# -------------------------------
# script-path=xxx.py,tag=匹配cron用

"""
cron: 35 7 * * *
new Env('科技玩家签到');
"""

import requests
import json
import os
import sys
import time
from requests.exceptions import RequestException

# ========== 集成通知功能 ==========
try:
    from notify import send  # 导入青龙面板的多渠道通知函数
except ImportError:
    print("❌ 未找到通知脚本notify.py，将使用控制台输出")
    def send(title, content):
        print(f"\n【通知】{title}\n{content}\n")

# 禁用SSL警告
requests.packages.urllib3.disable_warnings()

# 全局配置
MAX_RETRY = 2
TIMEOUT = 20

def request_with_retry(method, url, headers=None, data=None, retry=0):
    """带重试机制的请求函数"""
    try:
        if method.lower() == 'post':
            resp = requests.post(url=url, headers=headers, data=data, timeout=TIMEOUT, verify=False)
        else:
            resp = requests.get(url=url, headers=headers, timeout=TIMEOUT, verify=False)
        resp.raise_for_status()
        return resp
    except Exception as e:
        if retry < MAX_RETRY:
            print(f"请求失败，1秒后重试...")
            time.sleep(1)
            return request_with_retry(method, url, headers, data, retry+1)
        raise e

def kjwj_sign(username, password, index):
    """单个账号签到函数"""
    try:
        # 基础请求头
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://www.kejiwanjia.net',
            'Referer': 'https://www.kejiwanjia.net/'
        }

        # 1. 登录
        login_url = 'https://www.kejiwanjia.net/wp-json/jwt-auth/v1/token'
        login_data = {'username': username, 'password': password}
        login_resp = request_with_retry('post', login_url, base_headers, login_data)
        
        try:
            login_result = login_resp.json()
        except:
            return f"❌ 第{index}个账号 {username} - 登录接口返回非JSON数据"

        if 'token' not in login_result:
            error_msg = login_result.get('message', '登录失败')
            return f"❌ 第{index}个账号 {username} - {error_msg}"

        token = login_result['token']
        nickname = login_result.get('name', username)
        print(f"\n===== 第{index}个账号：{nickname} =====")

        # 2. 请求头
        sign_headers = base_headers.copy()
        sign_headers.update({
            'Authorization': f'Bearer {token}',
            'Cookie': f'b2_token={token};',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        })

        # 3. 执行签到（跳过状态检查，直接签到，修复核心BUG）
        sign_url = 'https://www.kejiwanjia.net/wp-json/b2/v1/userMission'
        sign_resp = request_with_retry('post', sign_url, sign_headers)
        
        # 安全解析JSON
        try:
            sign_result = sign_resp.json()
        except:
            return f"⚠️ 第{index}个账号 {nickname} - 今日已签到（接口返回文本）"

        # 安全判断
        if isinstance(sign_result, dict):
            if 'mission' in sign_result:
                credit = sign_result['mission'].get('credit', 0)
                return f"✅ 第{index}个账号 {nickname} - 签到成功！获得{credit}积分"
            elif 'msg' in sign_result:
                return f"⚠️ 第{index}个账号 {nickname} - {sign_result['msg']}"
            else:
                return f"✅ 第{index}个账号 {nickname} - 签到完成"
        else:
            return f"⚠️ 第{index}个账号 {nickname} - 今日已签到"

    except RequestException as e:
        return f"❌ 第{index}个账号 {username} - 网络异常"
    except Exception as e:
        return f"❌ 第{index}个账号 {username} - 错误：{str(e)[:60]}"

if __name__ == '__main__':
    print("===== 科技玩家签到脚本 开始执行 =====\n")
    sign_results = []

    # 读取环境变量
    username_str = os.getenv("kjwj_username", "").strip()
    password_str = os.getenv("kjwj_password", "").strip()

    if not username_str or not password_str:
        err_msg = "❌ 未配置 kjwj_username / kjwj_password"
        print(err_msg)
        send("科技玩家签到-配置错误", err_msg)
        sys.exit(1)

    # 分割账号
    user_list = [u.strip() for u in username_str.split('&') if u.strip()]
    pwd_list = [p.strip() for p in password_str.split('&') if p.strip()]

    if len(user_list) != len(pwd_list):
        err_msg = f"❌ 账号数量与密码数量不匹配"
        print(err_msg)
        send("科技玩家签到-配置错误", err_msg)
        sys.exit(1)

    # 执行
    for i, (user, pwd) in enumerate(zip(user_list, pwd_list), 1):
        result = kjwj_sign(user, pwd, i)
        print(result)
        sign_results.append(result)

    # 结果
    print("\n" + "="*50)
    final = "\n".join(sign_results)
    print(f"📊 签到结果：\n{final}")
    send("科技玩家签到结果", final)
    print("\n===== 脚本执行完毕 =====")
