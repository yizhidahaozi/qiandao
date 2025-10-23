#!/usr/bin/python3
#修改时间：2025年11月9日16点00分（适配aid=250-813固定范围）
# -- coding: utf-8 --
# -------------------------------
# @功能：富贵论坛签到+固定范围活动评论（250-822）
# @核心：ID区间遍历+去重评论+精准接口匹配
# -------------------------------

import requests
import re
import time
import json
import os
import sys
import random
import urllib.parse
from datetime import datetime

try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"\n【📢 通知】{title}\n{content}")

class FGLTActivityTask:
    def __init__(self, cookies):
        # 1. 核心配置（固定ID范围）
        self.base_url = "https://www.fglt.net/"
        self.comment_api_url = f"{self.base_url}plugin.php?id=proalsupport&modac=post&submodac=comment"
        self.min_aid = 250  # 起始ID
        self.max_aid = 813  # 结束ID
        self.cookies = self._filter_valid_cookies(cookies)
        self.headers = self._get_headers()
        
        # 2. 数据存储（防重复）
        self.data_file = "fgl_activity_comment.json"
        self.user_data = {
            "sign_status": {},
            "commented_aids": set()  # 已评论ID记录
        }
        self._load_data()
        
        # 3. 评论配置
        self.min_comment = 5
        self.max_comment = 14
        self.daily_comment = random.randint(self.min_comment, self.max_comment)
        self.comment_interval = (7, 15)  # 随机间隔防反爬
        self.comment_content = ["支持", "富贵", "支持富贵", "支持 富贵"]
        self.results = []

    def _filter_valid_cookies(self, cookies):
        """过滤有效的登录Cookie"""
        valid = []
        for cookie in cookies:
            cookie = cookie.strip()
            if cookie and "JoRn_2132_saltkey" in cookie and "JoRn_2132_auth" in cookie:
                valid.append(cookie)
            elif cookie:
                print(f"⚠️ 跳过无效Cookie：{cookie[:20]}...")
        return valid

    def _get_headers(self):
        """构造请求头（模拟浏览器）"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
        ]
        return {
            "Host": "www.fglt.net",
            "Origin": "https://www.fglt.net",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": f"{self.base_url}plugin.php?id=proalsupport",
            "User-Agent": random.choice(user_agents),
            "X-Requested-With": "XMLHttpRequest"
        }

    def _load_data(self):
        """加载已评论记录和签到状态"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.user_data["sign_status"] = loaded.get("sign_status", {})
                    self.user_data["commented_aids"] = set(loaded.get("commented_aids", []))
                print(f"✅ 加载历史数据：已评论{len(self.user_data['commented_aids'])}个活动（范围250-813）")
        except Exception as e:
            print(f"⚠️ 加载数据失败：{str(e)}")

    def _save_data(self):
        """保存已评论记录"""
        try:
            save_data = {
                "sign_status": self.user_data["sign_status"],
                "commented_aids": list(self.user_data["commented_aids"])
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print("✅ 数据保存成功")
        except Exception as e:
            print(f"❌ 保存数据失败：{str(e)}")

    # ------------------------------
    # 1. 自动签到（稳定逻辑）
    # ------------------------------
    def _get_username(self, session):
        """提取用户名"""
        username = "未知用户"
        try:
            resp = session.get(f"{self.base_url}home.php?mod=space", timeout=15)
            match = re.search(r'<h2 class="mt"\s*>(.*?)</h2>', resp.text, re.S)
            if match and match.group(1).strip():
                username = match.group(1).strip()
                return username
        except:
            try:
                resp = session.get(self.base_url, timeout=15)
                match = re.search(r'欢迎(您回来，|)([^<]{2,20})<', resp.text, re.S)
                if match:
                    username = match.group(2).strip()
            except:
                pass
        return username

    def _get_formhash(self, session):
        """获取formhash（评论必需参数）"""
        try:
            resp = session.get(f"{self.base_url}plugin.php?id=proalsupport", timeout=15)
            match = re.search(r'formhash=(.*?)["&]', resp.text)
            if match:
                return match.group(1)
        except Exception as e:
            print(f"❌ 获取formhash失败：{str(e)}")
        return None

    def do_sign(self, session, cookie_dict, account_idx):
        """执行签到"""
        username = self._get_username(session)
        sign_ip = cookie_dict.get("JoRn_2132_lip", "未知").split(",")[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n===== 账号{account_idx}（{username}）- 签到任务 =====")

        if username in self.user_data["sign_status"] and self.user_data["sign_status"][username] == today:
            result = f"👤 {username}\n📝 签到：今日已完成\n🌐 IP：{sign_ip}\n⏰ {now}"
            self.results.append(result)
            print(result)
            return session

        formhash = self._get_formhash(session)
        if not formhash:
            result = f"👤 {username}\n📝 签到：失败（无formhash）\n🌐 IP：{sign_ip}\n⏰ {now}"
            self.results.append(result)
            print(result)
            return session

        sign_url = f"{self.base_url}plugin.php?id=dsu_amupper&ppersubmit=true&formhash={formhash}&infloat=yes&handlekey=dsu_amupper&inajax=1&ajaxtarget=fwin_content_dsu_amupper"
        success = False
        for _ in range(2):
            try:
                time.sleep(random.uniform(2, 4))
                resp = session.post(sign_url, timeout=20)
                if "签到成功" in resp.text or "已签到" in resp.text:
                    success = True
                    break
            except:
                time.sleep(3)

        if success:
            self.user_data["sign_status"][username] = today
            self._save_data()
            result = f"👤 {username}\n📝 签到：成功（+1经验）\n🌐 IP：{sign_ip}\n⏰ {now}"
        else:
            result = f"👤 {username}\n📝 签到：失败（响应异常）\n🌐 IP：{sign_ip}\n⏰ {now}"
        self.results.append(result)
        print(result)
        return session

    # ------------------------------
    # 2. 活动评论（核心：固定ID范围250-813）
    # ------------------------------
    def _get_activity_posts(self):
        """生成250-813之间未评论的ID列表"""
        posts = []
        # 从大到小遍历（优先评论较新帖子）
        for aid in range(self.max_aid, self.min_aid - 1, -1):
            aid_str = str(aid)
            if aid_str not in self.user_data["commented_aids"]:
                posts.append({
                    "aid": aid_str,
                    "url": f"{self.base_url}plugin.php?id=proalsupport&modac=post&submodac=detail&aid={aid_str}"
                })
        print(f"✅ 生成可评论活动：{len(posts)}个（ID范围250-813）")
        return posts

    def do_activity_comments(self, session, username):
        """执行评论（遍历250-813未评论ID）"""
        print(f"\n===== {username} - 评论任务（今日{self.daily_comment}条） =====")
        posts = self._get_activity_posts()
        if not posts:
            self.results.append("📊 评论：250-813范围已全部评论完毕")
            return

        comment_count = 0
        formhash = self._get_formhash(session)
        if not formhash:
            self.results.append("📊 评论：失败（无法获取formhash）")
            return

        for post in posts:
            if comment_count >= self.daily_comment:
                break

            aid = post["aid"]
            try:
                # 随机评论内容
                content = random.choice(self.comment_content)
                # 构造评论参数
                comment_params = {
                    "formhash": formhash,
                    "aid": aid,
                    "content": content
                }
                # 随机间隔7-15秒
                interval = random.uniform(*self.comment_interval)
                print(f"⏳ 等待{interval:.1f}秒，评论ID：{aid}...")
                time.sleep(interval)

                # 发送评论请求
                resp = session.post(self.comment_api_url, data=comment_params, timeout=15)
                resp_text = resp.text.strip()

                # 验证评论结果
                try:
                    resp_json = json.loads(resp_text)
                    if resp_json.get("rs") == 200 and resp_json.get("msg") == "评论成功":
                        comment_count += 1
                        self.user_data["commented_aids"].add(aid)
                        print(f"✅ 评论{comment_count}/{self.daily_comment}：{content}（ID：{aid}）")
                    else:
                        print(f"❌ 评论失败（ID：{aid}）：{resp_json.get('msg', '无效帖子')}")
                except json.JSONDecodeError:
                    print(f"❌ 响应异常（ID：{aid}）：{resp_text[:50]}")
            except Exception as e:
                print(f"❌ 评论出错（ID：{aid}）：{str(e)}")
                continue

        self._save_data()
        self.results.append(f"📊 评论：完成{comment_count}/{self.daily_comment}条（剩余可评：{len(posts)-comment_count}）")

    # ------------------------------
    # 主流程
    # ------------------------------
    def run(self):
        if not self.cookies:
            print("❌ 未检测到有效Cookie，请配置fg_cookies")
            send("富贵论坛任务", "未检测到有效Cookie")
            return

        start_delay = random.uniform(3, 7)
        print(f"✅ 检测到{len(self.cookies)}个账号，{start_delay:.1f}秒后启动...")
        time.sleep(start_delay)

        for idx, cookie in enumerate(self.cookies, 1):
            session = requests.Session()
            session.headers.update(self.headers)
            cookie_dict = {}
            for item in urllib.parse.unquote(cookie).split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookie_dict[k] = v
            session.cookies.update(cookie_dict)

            # 验证登录状态
            login_valid = False
            try:
                resp = session.get(self.base_url, timeout=15)
                login_valid = "退出" in resp.text
            except:
                pass

            if not login_valid:
                result = f"👤 未知用户\n❌ 状态：Cookie失效"
                self.results.append(result)
                print(result)
                continue

            # 执行签到
            session = self.do_sign(session, cookie_dict, idx)

            # 执行评论
            username = self._get_username(session)
            self.do_activity_comments(session, username)

            # 多账号间隔
            if idx < len(self.cookies):
                time.sleep(random.uniform(10, 15))

        # 发送通知
        notify_content = "\n\n".join(self.results)
        send("富贵论坛任务结果", notify_content)
        print("\n✅ 所有任务执行完毕！")

if __name__ == "__main__":
    cookies = os.getenv("fg_cookies", "").split("&")
    cookies = [c for c in cookies if c.strip()]
    if not cookies:
        print("❌ 请设置fg_cookies环境变量（格式：Cookie1&Cookie2）")
        sys.exit(1)
    task = FGLTActivityTask(cookies)
    task.run()
    sys.exit(0)
