#!/usr/bin/python3
# -- coding: utf-8 --
# -------------------------------
# @Author : github@wd210010 https://github.com/wd210010/just_for_happy
# @Time : 2023/2/27 13:23
# -------------------------------
# cron "30 7 * * *" script-path=xxx.py,tag=匹配cron用
# const $ = new Env('科技玩家签到')

import requests
import json
import os
from requests.exceptions import RequestException

# 禁用请求警告
requests.packages.urllib3.disable_warnings()

def kjwj_sign(username, password, index):
    """
    单个账号签到函数
    :param username: 账号（邮箱）
    :param password: 密码
    :param index: 账号序号
    :return: 签到结果字符串
    """
    try:
        # 1. 获取登录token
        login_url = 'https://www.kejiwanjia.net/wp-json/jwt-auth/v1/token'
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
            'origin': 'https://www.kejiwanjia.net',
            'referer': 'https://www.kejiwanjia.net/'
        }
        data = {'username': username, 'password': password}
        
        # 发送登录请求（添加超时和SSL验证关闭）
        login_resp = requests.post(
            url=login_url,
            headers=headers,
            data=data,
            timeout=15,
            verify=False
        )
        login_resp.raise_for_status()  # 触发HTTP状态码异常
        login_result = login_resp.json()

        # 校验登录结果
        if 'token' not in login_result or 'name' not in login_result:
            error_msg = login_result.get('message', '未知错误')
            return f"第{index}个账号 {username} - 登录失败：{error_msg}"

        token = login_result['token']
        nickname = login_result['name']
        print(f"\n===== 开始处理第{index}个账号：{nickname}（{username}） =====")

        # 2. 构建签到请求头
        sign_headers = {
            'Host': 'www.kejiwanjia.net',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'authorization': f'Bearer {token}',
            'cookie': f'b2_token={token};',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36'
        }

        # 3. 检查签到状态
        check_url = 'https://www.kejiwanjia.net/wp-json/b2/v1/getUserMission'
        check_resp = requests.post(
            url=check_url,
            headers=sign_headers,
            timeout=15,
            verify=False
        )
        check_resp.raise_for_status()
        check_result = check_resp.json()

        # 提取签到积分（增加容错）
        current_credit = check_result.get('mission', {}).get('credit', -1)

        if current_credit == 0:
            # 4. 执行签到
            sign_url = 'https://www.kejiwanjia.net/wp-json/b2/v1/userMission'
            sign_resp = requests.post(
                url=sign_url,
                headers=sign_headers,
                timeout=15,
                verify=False
            )
            sign_resp.raise_for_status()
            sign_result = sign_resp.json()
            
            # 解析签到结果
            sign_credit = sign_result.get('mission', {}).get('credit', '未知')
            return f"第{index}个账号 {nickname} - 签到成功，获得 {sign_credit} 积分"
        elif current_credit > 0:
            return f"第{index}个账号 {nickname} - 今日已签到，累计获得 {current_credit} 积分"
        else:
            return f"第{index}个账号 {nickname} - 无法获取签到状态，接口返回：{check_result}"

    except RequestException as e:
        return f"第{index}个账号 {username} - 网络异常：{str(e)}"
    except json.JSONDecodeError:
        return f"第{index}个账号 {username} - 接口返回非JSON格式数据"
    except Exception as e:
        return f"第{index}个账号 {username} - 未知错误：{str(e)}"

if __name__ == '__main__':
    print("===== 科技玩家签到脚本开始执行 =====")
    
    # 读取青龙环境变量（增加空值校验）
    username_str = os.getenv("kjwj_username", "")
    password_str = os.getenv("kjwj_password", "")
    
    if not username_str or not password_str:
        print("错误：未配置 kjwj_username 或 kjwj_password 环境变量！")
        exit(1)
    
    # 分割多账号（&分隔）
    kjwj_username = username_str.split('&')
    kjwj_password = password_str.split('&')
    
    # 校验账号密码数量是否匹配
    if len(kjwj_username) != len(kjwj_password):
        print(f"错误：账号数量（{len(kjwj_username)}）与密码数量（{len(kjwj_password)}）不匹配！")
        exit(1)
    
    # 批量执行签到
    for idx, (user, pwd) in enumerate(zip(kjwj_username, kjwj_password), 1):
        result = kjwj_sign(user.strip(), pwd.strip(), idx)
        print(result)
    
    print("\n===== 科技玩家签到脚本执行结束 =====")
