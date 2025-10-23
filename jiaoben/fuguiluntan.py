#!/usr/bin/python3
#修改时间：2025年10月24日10点00分（移除历史文件不存在提示）
# -- coding: utf-8 --
# -------------------------------
# @Author : 富贵论坛签到（优化版） 🚀
# @Time : 2025/10/24
# 功能：自动签到+状态二次校验+失败重试+精简输出
# -------------------------------
# cron "0 8 * * *" script-path=xxx.py,tag=富贵论坛签到 ⏰
# const $ = new Env('富贵论坛签到'); 🌐

import requests
import re
import time
import json
import os
import sys
import random
import urllib.parse
from datetime import datetime

# 通知模块兼容（青龙/本地）
try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"\n【📢 通知】{title}\n{content}")

class FGLTSignWithFormat:
    def __init__(self, cookies):
        # 基础配置
        self.base_url = "https://www.fglt.net/"
        self.cookies = self._filter_valid_cookies(cookies)
        self.headers = self._get_browser_headers()
        
        # 仅保留签到状态用于重复校验（不创建新文件）
        self.user_data = {"sign_status": {}}
        self.load_sign_data()
        
        self.final_results = []

    def _filter_valid_cookies(self, cookies):
        """过滤含核心登录字段的Cookie"""
        valid = []
        for cookie in cookies:
            cookie = cookie.strip()
            if cookie and "JoRn_2132_saltkey" in cookie and "JoRn_2132_auth" in cookie:
                valid.append(cookie)
            elif cookie:
                print(f"⚠️ 跳过无效Cookie：{cookie[:20]}...")
        return valid

    def _get_browser_headers(self):
        """增强版请求头（防反爬优化）"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
        ]
        return {
            "Host": "www.fglt.net",
            "Origin": "https://www.fglt.net",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": f"{self.base_url}plugin.php?id=dsu_amupper",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": random.choice(user_agents),
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

    def load_sign_data(self):
        """加载历史签到状态（文件不存在时不提示）"""
        try:
            if os.path.exists("fgl_sign_format.log"):
                with open("fgl_sign_format.log", "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    self.user_data["sign_status"] = loaded_data.get("sign_status", {})
                print(f"✅ 加载历史签到状态：{len(self.user_data['sign_status'])}个用户")
        except Exception as e:
            print(f"⚠️ 加载数据失败（重置）：{str(e)}")
            self.user_data = {"sign_status": {}}

    def save_sign_data(self):
        """保存签到状态（仅文件已存在时，移除不存在提示）"""
        try:
            if os.path.exists("fgl_sign_format.log"):
                with open("fgl_sign_format.log", "w", encoding="utf-8") as f:
                    json.dump(self.user_data, f, ensure_ascii=False, indent=2)
                print("✅ 签到状态已保存")
            # 完全移除“历史数据文件不存在”的提示输出
        except Exception as e:
            print(f"❌ 保存数据失败：{str(e)}")

    def get_sign_ip(self, cookie_dict):
        """从Cookie提取IP"""
        lip_value = cookie_dict.get("JoRn_2132_lip", "")
        if lip_value and "," in lip_value:
            return lip_value.split(",")[0].strip()
        elif lip_value:
            return lip_value.strip()
        else:
            return "未知"

    def get_exact_username(self, session):
        """精准提取用户名（多场景适配）"""
        username = "未知用户"
        print("\n【🔍 提取用户名】开始匹配...")

        # 场景1：个人空间（优先）
        try:
            resp = session.get(f"{self.base_url}home.php?mod=space", timeout=15)
            resp.encoding = "utf-8"
            match = re.search(r'<h2 class="mt"\s*>(.*?)</h2>', resp.text, re.S)
            if match:
                extracted = match.group(1).strip()
                if len(extracted) <= 20 and "http" not in extracted:
                    username = extracted
                    print(f"✅ 从个人空间提取：{username}")
                    return username
            print("ℹ️ 场景1（个人空间）未匹配到")
        except Exception as e:
            print(f"ℹ️ 场景1失败：{str(e)}")

        # 场景2：空间设置页（备选）
        try:
            resp = session.get(f"{self.base_url}home.php?mod=spacecp", timeout=15)
            resp.encoding = "utf-8"
            match = re.search(r'<em>用户名[:：]</em>\s*<span>(.*?)</span>', resp.text, re.S)
            if match:
                username = match.group(1).strip()
                print(f"✅ 从空间设置提取：{username}")
                return username
            print("ℹ️ 场景2（空间设置）未匹配到")
        except Exception as e:
            print(f"ℹ️ 场景2失败：{str(e)}")

        # 场景3：首页欢迎语（兜底）
        try:
            resp = session.get(self.base_url, timeout=15)
            resp.encoding = "utf-8"
            match = re.search(r'欢迎(您回来，|)([^<]{2,20})<', resp.text, re.S)
            if match and match.group(2).strip():
                username = match.group(2).strip()
                print(f"✅ 从首页欢迎语提取：{username}")
                return username
            print("ℹ️ 场景3（首页）未匹配到")
        except Exception as e:
            print(f"ℹ️ 场景3失败：{str(e)}")

        return username

    def get_formhash(self, session):
        """多页面重试获取formhash"""
        target_pages = [
            (f"{self.base_url}plugin.php?id=dsu_amupper", "签到页"),
            (f"{self.base_url}forum.php", "论坛首页"),
            (f"{self.base_url}home.php?mod=spacecp", "空间设置页")
        ]
        for page_url, page_name in target_pages:
            time.sleep(random.uniform(1, 2))
            try:
                resp = session.get(page_url, timeout=15)
                resp.encoding = "utf-8"
                if "请登录" in resp.text:
                    print(f"❌ {page_name}检测到未登录，Cookie失效")
                    return None
                match = re.search(r'<input type="hidden" name="formhash" value="(.*?)" />', resp.text)
                if match:
                    formhash = match.group(1)
                    print(f"✅ 从{page_name}获取formhash：{formhash[:6]}...")
                    return formhash
                print(f"ℹ️ {page_name}未找到formhash")
            except Exception as e:
                print(f"❌ 访问{page_name}失败：{str(e)}")
        return None

    def verify_sign_status(self, session):
        """二次校验签到状态（访问签到页确认）"""
        try:
            resp = session.get(f"{self.base_url}plugin.php?id=dsu_amupper", timeout=15)
            resp.encoding = "utf-8"
            return "您已签到完毕" in resp.text or "今日已签到" in resp.text
        except Exception as e:
            print(f"⚠️ 二次校验失败：{str(e)}")
            return False

    def sign_single_account(self, cookie, account_idx):
        """单个账号签到（含重试+二次校验）"""
        session = requests.Session()
        session.headers.update(self.headers)
        cookie_dict = {}
        decoded_cookie = urllib.parse.unquote(cookie)
        for item in decoded_cookie.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookie_dict[key] = value
        session.cookies.update(cookie_dict)

        # 校验登录状态
        login_valid = False
        try:
            resp = session.get(self.base_url, timeout=15)
            login_valid = "退出" in resp.text
        except Exception as e:
            print(f"❌ 登录校验失败：{str(e)}")
        
        if not login_valid:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sign_ip = self.get_sign_ip(cookie_dict)
            result = f"👤 用户名：未知（Cookie无效）\n" \
                     f"ℹ️ 签到状态：Cookie失效，无法登录\n" \
                     f"🌐 签到IP：{sign_ip}（来自Cookie）\n" \
                     f"⏰ 签到时间：{current_time}"
            self.final_results.append(result)
            print(f"\n{result}")
            return

        # 提取关键信息
        username = self.get_exact_username(session)
        sign_ip = self.get_sign_ip(cookie_dict)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_str = datetime.now().strftime("%Y-%m-%d")
        print(f"\n===== 处理账号{account_idx}（{username}）=====")

        # 检查重复签到（基于历史状态）
        if username in self.user_data["sign_status"] and self.user_data["sign_status"][username] == today_str:
            result = f"👤 用户名：{username}\n" \
                     f"ℹ️ 签到状态：今日已签到，无需重复操作\n" \
                     f"🌐 签到IP：{sign_ip}（来自Cookie）\n" \
                     f"⏰ 签到时间：{current_time}"
            self.final_results.append(result)
            print(result)
            return

        # 获取formhash
        formhash = self.get_formhash(session)
        if not formhash:
            result = f"👤 用户名：{username}\n" \
                     f"ℹ️ 签到状态：获取formhash失败\n" \
                     f"🌐 签到IP：{sign_ip}（来自Cookie）\n" \
                     f"⏰ 签到时间：{current_time}"
            self.final_results.append(result)
            print(result)
            return

        # 执行签到（含重试机制）
        sign_url = f"{self.base_url}plugin.php?id=dsu_amupper&ppersubmit=true&formhash={formhash}&infloat=yes&handlekey=dsu_amupper&inajax=1&ajaxtarget=fwin_content_dsu_amupper"
        retry_count = 1  # 最多重试1次
        resp_text = ""
        for retry in range(retry_count + 1):
            try:
                time.sleep(random.uniform(3, 5))  # 随机延迟，防反爬
                resp = session.post(sign_url, timeout=20)  # 延长超时时间
                resp.encoding = "utf-8"
                resp_text = resp.text
                print(f"✅ 第{retry+1}次签到请求成功，响应：{resp_text[:100]}")
                break
            except Exception as e:
                if retry < retry_count:
                    print(f"⚠️ 第{retry+1}次请求失败，{retry_count - retry}次重试中...")
                    time.sleep(random.uniform(3, 5))
                else:
                    result = f"👤 用户名：{username}\n" \
                             f"ℹ️ 签到状态：请求失败（{str(e)}）\n" \
                             f"🌐 签到IP：{sign_ip}（来自Cookie）\n" \
                             f"⏰ 签到时间：{current_time}"
                    self.final_results.append(result)
                    print(result)
                    return

        # 二次校验签到状态
        is_signed = self.verify_sign_status(session)
        self.user_data["sign_status"][username] = today_str
        self.save_sign_data()  # 调用保存方法（无文件时不输出提示）

        # 生成结果
        if is_signed:
            result = f"👤 用户名：{username}\n" \
                     f"ℹ️ 签到状态：今日已签到（二次校验确认）\n" \
                     f"🌐 签到IP：{sign_ip}（来自Cookie）\n" \
                     f"⏰ 签到时间：{current_time}"
        elif "您已签到完毕" in resp_text or "今日已签到" in resp_text:
            result = f"👤 用户名：{username}\n" \
                     f"ℹ️ 签到状态：今日已签到（响应确认）\n" \
                     f"🌐 签到IP：{sign_ip}（来自Cookie）\n" \
                     f"⏰ 签到时间：{current_time}"
        elif "签到成功" in resp_text:
            result = f"👤 用户名：{username}\n" \
                     f"ℹ️ 签到状态：今日首次签到成功\n" \
                     f"🌐 签到IP：{sign_ip}（来自Cookie）\n" \
                     f"⏰ 签到时间：{current_time}"
        else:
            result = f"👤 用户名：{username}\n" \
                     f"ℹ️ 签到状态：签到异常（响应未明确）\n" \
                     f"🌐 签到IP：{sign_ip}（来自Cookie）\n" \
                     f"⏰ 签到时间：{current_time}"

        self.final_results.append(result)
        print(result)

    def run_batch_sign(self):
        if not self.cookies:
            error_msg = "❌ 未检测到有效Cookie，请配置fg_cookies环境变量"
            print(error_msg)
            send("富贵论坛签到 - 错误", error_msg)
            return

        # 启动延迟
        start_delay = random.uniform(3, 8)
        print(f"✅ 共检测到{len(self.cookies)}个有效账号，{start_delay:.1f}秒后启动...")
        time.sleep(start_delay)

        # 逐个签到
        for idx, cookie in enumerate(self.cookies, 1):
            self.sign_single_account(cookie, idx)
            if idx < len(self.cookies):
                inter_delay = random.uniform(5, 10)
                print(f"\nℹ️ 等待{inter_delay:.1f}秒处理下一个账号...")
                time.sleep(inter_delay)

        # 发送通知
        notify_content = "\n".join(self.final_results)
        send("富贵论坛签到结果", notify_content)
        print("\n✅ 脚本执行完毕！")

# 主程序入口
if __name__ == "__main__":
    env_cookies = os.getenv("fg_cookies", "")
    if not env_cookies:
        print("❌ 请配置fg_cookies环境变量（格式：Cookie1&Cookie2）")
        sys.exit(1)
    cookie_list = [c.strip() for c in env_cookies.split("&") if c.strip()]
    signer = FGLTSignWithFormat(cookie_list)
    signer.run_batch_sign()
    sys.exit(0)
