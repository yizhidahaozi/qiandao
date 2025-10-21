#!/usr/bin/env python3
#修改时间：2025年10月21日16点11分
# -*- coding: utf-8 -*-
# cron:6 6 * * *
# const $ = new Env("[mokey]奇妙应用自动签到")
# 作者：QUAN_GE
# 定制：通知仅含5行（版本+账号+签到+爆金币+总金币）

import requests
import datetime
import json
import sys
import random
import re
from time import sleep
from datetime import timezone, timedelta

# -------------------------- 通知依赖 --------------------------
try:
    from notify import send
except ImportError:
    print("❌ 未找到notify.py，请检查路径！")
    sys.exit()

# -------------------------- 基础配置 --------------------------
TZ = timezone(timedelta(hours=8))
REMOTE_CONFIG_URL = "https://mokeyqlapi.120322.xyz/now.json"
TIMEOUT = 15
SLEEP_TIME = [1, 3]


def get_env(env_name):
    """获取环境变量（仅返回值和错误）"""
    try:
        envs = QLAPI.getEnvs({"searchValue": env_name})
        if not envs.get("data"):
            return None, f"未找到{env_name}"
        env_data = envs["data"][0]
        if env_data["name"] != env_name:
            return None, f"{env_name}名称不匹配"
        return env_data["value"], None
    except Exception as e:
        return None, f"获取{env_name}失败：{str(e)}"


def get_remote_config():
    """获取远程配置（修复run字段缺失）"""
    try:
        sleep_t = random.randint(SLEEP_TIME[0], SLEEP_TIME[1])
        print(f"⏳ 随机等待{sleep_t}秒...")
        sleep(sleep_t)
        
        resp = requests.get(REMOTE_CONFIG_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        config = resp.json()
        
        if "run" not in config:
            config["run"] = "yes"
            print(f"⚠️  远程缺少run字段，自动设为run=yes")
        if "now" not in config:
            return None, "远程缺少now字段（版本信息）"
        
        return config, None
    except requests.exceptions.RequestException as e:
        return None, f"远程请求失败：{str(e)}"
    except json.JSONDecodeError:
        return None, "远程响应不是有效JSON"


def get_custom_sign_result(remote_config, user_id, token):
    """生成5行定制通知内容（严格匹配要求顺序）"""
    custom_result = []
    headers = {
        'token': token,
        'Host': 'www.magicalapp.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.magicalapp.cn/'
    }

    # 1. 版本状态（第1行）
    current_version = "1.3.1"
    latest_version = remote_config["now"]
    custom_result.append(f"🎉 当前为最新版（{current_version}）")

    # 2. 当前账号（第2行，新增）
    custom_result.append(f"📌 当前账号：{user_id}")

    # 3. 签到结果（第3行）
    sign_url = "http://www.magicalapp.cn/user/api/signDays"
    try:
        resp = requests.get(sign_url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        sign_data = resp.json()
        if isinstance(sign_data, dict) and sign_data.get("code") == "200":
            coin_sign = sign_data.get("data", {}).get("coin", 5)
            custom_result.append(f"✅ 签到成功，获得{coin_sign}枚金币")
        elif "今日已签" in str(sign_data):
            custom_result.append(f"📅 签到失败（今日已签）")
        else:
            resp_str = str(sign_data)[:60].replace("'", "").replace('"', '')  # 保留足够响应长度
            custom_result.append(f"❌ 签到失败（响应：{resp_str}）")
    except Exception as e:
        custom_result.append(f"❌ 签到失败（异常：{str(e)[:30]}）")

    # 4. 爆金币结果（第4行）
    burst_url = f"https://www.magicalapp.cn/api/game/api/getCoinP?userId={user_id}"
    coin_burst = 0
    try:
        resp = requests.get(burst_url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        burst_data = resp.json()
        if isinstance(burst_data, dict) and burst_data.get("code") == "200":
            coin_burst = burst_data.get("data", 0)
            custom_result.append(f"✅ 爆金币成功，获得{coin_burst}枚金币")
        else:
            custom_result.append(f"❌ 爆金币失败（响应异常）")
    except Exception as e:
        custom_result.append(f"❌ 爆金币失败（异常：{str(e)[:30]}）")

    # 5. 总金币（第5行）
    try:
        sign_coin_match = re.search(r"获得(\d+)枚金币", custom_result[2])  # 从第3行（索引2）提取签到金币
        coin_sign = int(sign_coin_match.group(1)) if sign_coin_match else 0
        total = coin_sign + coin_burst
        custom_result.append(f"💰 本次共获{total}枚金币")
    except:
        custom_result.append(f"💰 本次共获0枚金币")

    return custom_result


# -------------------------- 主执行流程 --------------------------
if __name__ == "__main__":
    print("🚀 奇妙应用自动签到启动（5行定制版）")

    try:
        # 1. 检查环境变量
        print("\n🔍 检查环境变量...")
        token, token_err = get_env("mokey_qmyy_token")
        user_id, uid_err = get_env("mokey_qmyy_id")
        
        if token_err or uid_err:
            err_msg = f"配置错误：{token_err or uid_err}"
            print(f"❌ {err_msg}")
            send("奇妙应用签到 - 配置错误", err_msg)
            sys.exit()
        print(f"✅ 环境变量通过（账号：{user_id}）")

        # 2. 获取远程配置
        print("\n🔍 获取远程配置...")
        remote_config, remote_err = get_remote_config()
        
        if remote_err:
            print(f"❌ 远程配置失败：{remote_err}")
            send("奇妙应用签到 - 远程配置失败", remote_err)
            sys.exit()
        print(f"✅ 远程配置通过（run={remote_config['run']}）")

        # 3. 检查运行权限
        print("\n🔍 检查运行权限...")
        if remote_config["run"] != "yes":
            err_msg = f"远程禁止运行（run={remote_config['run']}）"
            print(f"❌ {err_msg}")
            send("奇妙应用签到 - 运行禁止", err_msg)
            sys.exit()

        # 4. 生成5行核心结果并发送通知
        print("\n🔍 执行签到与爆金币...")
        final_result = get_custom_sign_result(remote_config, user_id, token)

        # 输出并发送通知
        print("\n📋 定制通知内容（5行）：")
        for line in final_result:
            print(line)
        
        send("奇妙应用自动签到结果", "\n".join(final_result))
        print("\n✅ 通知发送成功（仅5行定制内容）")

    except Exception as e:
        err_msg = f"脚本异常：{str(e)[:50]}"
        print(f"🚨 {err_msg}")
        send("奇妙应用签到 - 脚本异常", err_msg)
