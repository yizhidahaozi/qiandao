#!/usr/bin/python3
# -- coding: utf-8 --
# -------------------------------
# @Author : 富贵论坛签到（Cookie验证增强版） 🚀
# @Time : 2025/10/21
# 解决问题：Cookie未登录、特殊字符解析、请求头模拟
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

# 通知模块
try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"\n【通知】{title}\n{content}")

class FGLTCookieSigner:
    def __init__(self, cookies):
        self.cookies = self._filter_cookies(cookies)
        self.base_url = "https://www.fglt.net/"
        # 关键：模拟真实浏览器请求头（补充Host、Origin）
        self.headers = {
            "Host": "www.fglt.net",
            "Origin": "https://www.fglt.net",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": f"{self.base_url}forum.php",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }
        self.sign_log = "fgl_cookie_sign.log"
        self.last_sign_date = ""
        self.success_count = 0
        self.load_sign_log()
        self.results = []

    def _filter_cookies(self, cookies):
        """过滤空Cookie，并检查关键字段（JoRn_2132_*）"""
        valid = []
        for cookie in cookies:
            cookie = cookie.strip()
            if not cookie:
                continue
            # 检查是否包含富贵论坛必要的Cookie字段
            if "JoRn_2132_saltkey" in cookie and "JoRn_2132_auth" in cookie:
                valid.append(cookie)
            else:
                print(f"⚠️  Cookie缺失关键字段（JoRn_2132_saltkey/JoRn_2132_auth）：{cookie[:30]}...")
        return valid

    def load_sign_log(self):
        try:
            if os.path.exists(self.sign_log):
                with open(self.sign_log, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_sign_date = data["last_date"]
                    self.success_count = data["success_count"]
        except Exception as e:
            print(f"ℹ️  签到记录初始化：{str(e)}")

    def save_sign_log(self):
        try:
            data = {
                "last_date": self.last_sign_date,
                "success_count": self.success_count,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.sign_log, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存记录失败：{str(e)}")

    def _check_login_status(self, session):
        """验证Cookie是否已登录（访问首页看是否有“退出”按钮）"""
        try:
            resp = session.get(self.base_url, timeout=15)
            resp.encoding = "utf-8"
            # 打印页面片段（帮助排查是否跳登录页）
            print(f"\n【登录状态校验】页面片段：{resp.text[:500]}")
            # 论坛登录后会有“退出”按钮，未登录则有“登录”按钮
            if "退出" in resp.text or "安全退出" in resp.text:
                print("✅ Cookie登录状态有效")
                return True
            elif "登录" in resp.text or "请登录" in resp.text:
                print("❌ Cookie登录状态失效（页面提示登录）")
                return False
            else:
                print("⚠️  无法判断登录状态（页面无明确标识）")
                return False
        except Exception as e:
            print(f"❌ 登录校验失败：{str(e)}")
            return False

    def get_username(self, session):
        """从已登录页面提取用户名"""
        try:
            resp = session.get(f"{self.base_url}home.php?mod=space", timeout=15)
            resp.encoding = "utf-8"
            # 匹配Discuz论坛用户名标签（<span class="vwmy">）
            match = re.search(r'<span class="vwmy">(.*?)</span>', resp.text, re.S)
            if match:
                return re.sub(r'<[^>]+>', '', match.group(1)).strip()
            return "已登录用户"
        except Exception as e:
            print(f"⚠️ 获取用户名失败：{str(e)}")
            return "已登录用户"

    def get_formhash(self, session):
        """从已登录页面获取formhash"""
        try:
            resp = session.get(f"{self.base_url}plugin.php?id=dsu_amupper", timeout=15)
            resp.encoding = "utf-8"
            match = re.search(r'<input type="hidden" name="formhash" value="(.*?)" />', resp.text)
            if match:
                formhash = match.group(1)
                print(f"✅ 获取formhash：{formhash[:6]}...")
                return formhash
            print(f"⚠️ 未找到formhash，页面片段：{resp.text[:300]}")
            return None
        except Exception as e:
            print(f"❌ 获取formhash失败：{str(e)}")
            return None

    def sign_single(self, cookie, idx):
        """单个账号签到（先校验登录状态）"""
        session = requests.Session()
        session.headers.update(self.headers)
        
        # 关键：正确解析Cookie（处理%2B、%2F等特殊字符）
        cookie_dict = {}
        decoded_cookie = urllib.parse.unquote(cookie)
        for item in decoded_cookie.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookie_dict[key] = value
        session.cookies.update(cookie_dict)

        # 步骤1：先校验Cookie是否登录
        if not self._check_login_status(session):
            msg = f"❌ 账号{idx}：Cookie失效，无法签到"
            self.results.append(msg)
            return msg

        # 步骤2：获取用户名
        username = self.get_username(session)
        print(f"\n===== 处理账号{idx}（{username}）=====")

        # 步骤3：检查今日是否已签
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_sign_date == today:
            msg = f"ℹ️ 账号{idx}（{username}）：今日已签到"
            self.results.append(msg)
            return msg

        # 步骤4：获取formhash
        formhash = self.get_formhash(session)
        if not formhash:
            msg = f"❌ 账号{idx}（{username}）：获取formhash失败"
            self.results.append(msg)
            return msg

        # 步骤5：执行签到
        sign_url = f"{self.base_url}plugin.php?id=dsu_amupper&ppersubmit=true&formhash={formhash}&infloat=yes&handlekey=dsu_amupper&inajax=1&ajaxtarget=fwin_content_dsu_amupper"
        try:
            resp = session.post(sign_url, timeout=15)
            resp.encoding = "utf-8"
            print(f"【签到响应】状态码：{resp.status_code}，内容：{resp.text[:300]}")

            # 解析结果
            if "您已签到完毕" in resp.text or "签到成功" in resp.text:
                self.last_sign_date = today
                self.success_count += 1
                self.save_sign_log()
                msg = f"✅ 账号{idx}（{username}）：签到成功"
            else:
                msg = f"❌ 账号{idx}（{username}）：签到失败（{resp.text[:50]}）"
            self.results。append(msg)
            return msg
        except Exception as e:
            msg = f"❌ 账号{idx}（{username}）：请求异常（{str(e)}）"
            self.results。append(msg)
            return msg

    def run(self):
        if not self.cookies:
            msg = "❌ 无有效Cookie（需包含JoRn_2132_saltkey/JoRn_2132_auth）"
            print(msg)
            send("富贵论坛签到 - 错误", msg)
            return

        print(f"✅ 检测到{len(self.cookies)}个有效Cookie，准备签到")
        # 启动延迟（防反爬）
        start_delay = random.uniform(3, 8)
        print(f"ℹ️ 随机延迟{start_delay:.1f}秒后启动...")
        time.sleep(start_delay)

        # 逐个签到
        for idx, cookie 在 enumerate(self.cookies, 1):
            self.sign_single(cookie, idx)
            if idx < len(self.cookies):
                time.sleep(random.uniform(5, 10))

        # 汇总结果
        print("\n" + "="*50)
        print("📋 签到结果汇总")
        print("="*50)
        for res in self.results:
            print(res)
        success_num = sum(1 for res 在 self.results if "✅" 在 res 或 "ℹ️" 在 res)
        failed_num = len(self.results) - success_num
        summary = f"\n本次签到：{success_num}成功，{failed_num}失败"
        print(summary)
        send("富贵论坛签到结果"， "\n".join(self.results) + summary)

if __name__ == "__main__":
    # 从环境变量获取Cookie（直接适配你的fg_cookies格式）
    env_cookies = os.getenv("fg_cookies", "")
    if not env_cookies:
        print("❌ 请先配置fg_cookies环境变量")
        sys.exit(1)
    # 分割多账号Cookie（单个账号无需分割）
    cookie_list = env_cookies.split("&")
    # 执行签到
    signer = FGLTCookieSigner(cookie_list)
    signer.run()
    print("\n✅ 脚本执行完毕")
