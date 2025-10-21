#!/usr/bin/python3
# -- coding: utf-8 --
# -------------------------------
# @Author : 富贵论坛签到（精准用户名版） 🚀
# @Time : 2025/10/21
# 核心：适配 <h2 class="mt">用户名</h2> 结构提取名字
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

# 通知模块（青龙/本地兼容）
try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"\n【通知】{title}\n{content}")

class FGLTUserSigner:
    def __init__(self, cookies):
        self.cookies = self._filter_cookies(cookies)
        self.base_url = "https://www.fglt.net/"
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
        self.sign_log = "fgl_user_sign.json"  # 用户签到记录
        self.user_sign_status = {}  # 存储 {用户名: 最后签到日期}
        self.load_sign_log()
        self.results = []

    def _filter_cookies(self, cookies):
        """过滤含核心登录字段的有效Cookie"""
        valid = []
        for cookie in cookies:
            cookie = cookie.strip()
            if cookie and "JoRn_2132_saltkey" in cookie and "JoRn_2132_auth" in cookie:
                valid.append(cookie)
        return valid

    def load_sign_log(self):
        """加载用户签到记录"""
        try:
            if os.path.exists(self.sign_log):
                with open(self.sign_log, "r", encoding="utf-8") as f:
                    self.user_sign_status = json.load(f)
                print(f"✅ 加载签到记录：{list(self.user_sign_status.keys())[:1]}...")
            else:
                print("ℹ️ 未找到签到记录，将创建新记录")
        except Exception as e:
            print(f"⚠️ 加载记录失败：{str(e)}")
            self.user_sign_status = {}

    def save_sign_log(self):
        """保存用户签到记录"""
        try:
            with open(self.sign_log, "w", encoding="utf-8") as f:
                json.dump(self.user_sign_status, f, ensure_ascii=False, indent=2)
            print("✅ 保存用户签到记录成功")
        except Exception as e:
            print(f"❌ 保存记录失败：{str(e)}")

    def _check_login(self, session):
        """验证Cookie是否登录"""
        try:
            resp = session.get(self.base_url, timeout=15)
            resp.encoding = "utf-8"
            return "退出" in resp.text  # 登录后有“退出”按钮
        except Exception as e:
            print(f"❌ 登录校验失败：{str(e)}")
            return False

    def get_username(self, session):
        """精准提取用户名（适配 <h2 class="mt">用户名</h2> 结构）"""
        username = "未知用户"
        print("\n【提取用户名】适配用户空间结构...")

        # 关键：访问个人空间页，匹配 <h2 class="mt"> 内的用户名
        try:
            space_url = f"{self.base_url}home.php?mod=space"
            resp = session.get(space_url, timeout=15)
            resp.encoding = "utf-8"
            # 正则匹配：<h2 class="mt"> 标签内的文本（忽略空格和换行）
            match = re.search(r'<h2 class="mt"\s*>(.*?)</h2>', resp.text, re.S)
            if match:
                extracted = match.group(1).strip()
                # 过滤非用户名内容（长度合理、不含网址等）
                if len(extracted) <= 20 and "http" not in extracted:
                    username = extracted
                    print(f"✅ 从 <h2 class=\"mt\"> 提取到用户名：{username}")
                    return username
            print(f"ℹ️ 个人空间 <h2> 标签未匹配到有效用户名")
        except Exception as e:
            print(f"ℹ️ 个人空间请求失败：{str(e)}")

        # 兜底：尝试其他结构（备选逻辑）
        try:
            index_resp = session.get(self.base_url, timeout=15)
            index_resp.encoding = "utf-8"
            match = re.search(r'欢迎(您回来，|)(.*?)<', index_resp.text, re.S)
            if match and len(match.groups()) >=2 and match.group(2).strip():
                username = match.group(2).strip()
                print(f"✅ 从首页欢迎语提取用户名：{username}")
                return username
        except Exception:
            pass

        print(f"⚠️ 最终用户名：{username}（建议检查个人空间页结构）")
        return username

    def get_formhash(self, session):
        """获取签到所需formhash"""
        try:
            resp = session.get(f"{self.base_url}plugin.php?id=dsu_amupper", timeout=15)
            resp.encoding = "utf-8"
            match = re.search(r'<input type="hidden" name="formhash" value="(.*?)" />', resp.text)
            if match:
                formhash = match.group(1)
                print(f"✅ 获取formhash：{formhash[:6]}...")
                return formhash
            print("❌ 未找到formhash，签到终止")
            return None
        except Exception as e:
            print(f"❌ 获取formhash失败：{str(e)}")
            return None

    def sign_single(self, cookie, idx):
        """单个账号签到（区分首次/重复）"""
        session = requests.Session()
        session.headers.update(self.headers)
        
        # 解析Cookie（处理特殊字符）
        cookie_dict = {}
        decoded_cookie = urllib.parse.unquote(cookie)
        for item in decoded_cookie.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookie_dict[key] = value
        session.cookies.update(cookie_dict)

        # 登录状态校验
        if not self._check_login(session):
            msg = f"❌ 账号{idx}：Cookie失效，无法签到"
            self.results.append(msg)
            return msg

        # 提取用户名
        username = self.get_username(session)
        current_user = username
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n===== 处理账号{idx}（{current_user}）=====")

        # 检查重复签到（优先读本地记录）
        if current_user in self.user_sign_status and self.user_sign_status[current_user] == today:
            msg = f"ℹ️ 账号{idx}（{current_user}）：今日已签到，无需重复操作"
            self.results.append(msg)
            return msg

        # 获取formhash
        formhash = self.get_formhash(session)
        if not formhash:
            msg = f"❌ 账号{idx}（{current_user}）：获取formhash失败"
            self.results.append(msg)
            return msg

        # 执行签到请求
        sign_url = f"{self.base_url}plugin.php?id=dsu_amupper&ppersubmit=true&formhash={formhash}&infloat=yes&handlekey=dsu_amupper&inajax=1&ajaxtarget=fwin_content_dsu_amupper"
        try:
            resp = session.post(sign_url, timeout=15)
            resp.encoding = "utf-8"
            resp_text = resp.text
            print(f"【签到响应】状态码：{resp.status_code}")

            # 识别签到结果
            if "您已签到完毕" in resp_text or "今日已签到" in resp_text:
                self.user_sign_status[current_user] = today
                self.save_sign_log()
                msg = f"ℹ️ 账号{idx}（{current_user}）：今日已签到，无需重复操作"
            elif "签到成功" in resp_text or "恭喜" in resp_text:
                self.user_sign_status[current_user] = today
                self.save_sign_log()
                msg = f"✅ 账号{idx}（{current_user}）：今日首次签到成功"
            else:
                msg = f"❌ 账号{idx}（{current_user}）：签到失败（响应片段：{resp_text[:50]}）"

            self.results.append(msg)
            return msg
        except Exception as e:
            msg = f"❌ 账号{idx}（{current_user}）：请求异常（{str(e)}）"
            self.results.append(msg)
            return msg

    def run(self):
        """批量执行所有账号签到"""
        if not self.cookies:
            msg = "❌ 未检测到有效Cookie（需包含 JoRn_2132_saltkey/JoRn_2132_auth）"
            print(msg)
            send("富贵论坛签到 - 错误", msg)
            return

        print(f"✅ 共检测到 {len(self.cookies)} 个有效Cookie，开始签到流程...")
        # 随机延迟启动（防反爬）
        start_delay = random.uniform(3, 8)
        print(f"ℹ️ 随机延迟 {start_delay:.1f} 秒后启动...")
        time.sleep(start_delay)

        # 逐个账号签到
        for idx, cookie in enumerate(self.cookies, 1):
            self.sign_single(cookie, idx)
            # 账号间间隔
            if idx < len(self.cookies):
                inter_delay = random.uniform(5, 10)
                print(f"ℹ️ 等待 {inter_delay:.1f} 秒处理下一个账号...")
                time.sleep(inter_delay)

        # 汇总结果并发送通知
        print("\n" + "="*50)
        print("📋 富贵论坛签到结果汇总")
        print("="*50)
        final_content = ""
        for res in self.results:
            print(res)
            final_content += res + "\n"
        # 统计类型
        success_num = sum(1 for res in self.results if "✅" in res)
        repeat_num = sum(1 for res in self.results if "ℹ️" in res)
        failed_num = len(self.results) - success_num - repeat_num
        summary = f"\n本次签到统计：{success_num} 个首次成功，{repeat_num} 个重复签到，{failed_num} 个失败"
        print(summary)
        final_content += summary
        # 发送通知
        send("富贵论坛签到结果（精准用户名版）", final_content)

if __name__ == "__main__":
    # 从环境变量获取Cookie（多个用 & 分隔）
    env_cookies = os.getenv("fg_cookies", "")
    if not env_cookies:
        print("❌ 请先配置 fg_cookies 环境变量（需包含 JoRn_2132_saltkey 和 JoRn_2132_auth）")
        sys.exit(1)
    # 分割并过滤Cookie
    cookie_list = [c.strip() for c in env_cookies.split("&") if c.strip()]
    # 初始化并执行签到
    signer = FGLTUserSigner(cookie_list)
    signer.run()
    print("\n✅ 富贵论坛签到脚本执行完毕")
