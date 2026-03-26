#!/usr/bin/python3
# 定制版：ID 1231-1253 + 7天评论一次 + 每次1条
# const $ = new Env('富贵论坛')
# -- coding: utf-8 --

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
        self.base_url = "https://www.fglt.net/"
        self.comment_api_url = f"{self.base_url}plugin.php?id=proalsupport&modac=post&submodac=comment"

        # 评论ID范围 1231-1253
        self.min_aid = 1231
        self.max_aid = 1253

        self.cookies = self._filter_valid_cookies(cookies)
        self.headers = self._get_headers()
        
        self.data_file = "fgl_activity_comment.json"
        self.user_data = {
            "sign_status": {},
            "commented_records": {}
        }
        self._load_data()
        
        # ====================== 这里已改成 5 天 ======================
        self.recomment_interval = 604800  # 7天 = 604800 秒
        # ===========================================================
        self.daily_comment = 1            # 每次只评论 1 条
        
        self.comment_interval = (60, 120)
        self.sign_delay = (3, 8)
        self.account_switch_delay = (30, 60)
        self.page_load_delay = (2, 5)
        
        self.comment_content = [
            "支持富贵",
            "支持富贵越来越好！！！",
            "支持 富贵有你更精彩"
        ]
        self.results = []

    def _filter_valid_cookies(self, cookies):
        valid = []
        for cookie in cookies:
            cookie = cookie.strip()
            if cookie and "JoRn_2132_saltkey" in cookie and "JoRn_2132_auth" in cookie:
                valid.append(cookie)
            elif cookie:
                print(f"⚠️ 跳过无效Cookie：{cookie[:20]}...")
        return valid

    def _get_headers(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        ]
        accept_languages = [
            "zh-CN,zh;q=0.9",
            "zh-CN,zh;q=0.8,en;q=0.6"
        ]
        return {
            "Host": "www.fglt.net",
            "Origin": "https://www.fglt.net",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": random.choice(user_agents),
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": random.choice(accept_languages),
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }

    def _load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.user_data["sign_status"] = loaded.get("sign_status", {})
                    old_records = loaded.get("commented_aids", {})
                    if isinstance(old_records, list):
                        self.user_data["commented_records"] = {aid: 0 for aid in old_records}
                    else:
                        self.user_data["commented_records"] = loaded.get("commented_records", {})
        except Exception as e:
            pass

    def _save_data(self):
        try:
            save_data = {
                "sign_status": self.user_data["sign_status"],
                "commented_records": self.user_data["commented_records"]
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _safe_request(self, session, method, url, **kwargs):
        max_retries = 3
        for retry in range(max_retries):
            try:
                timeout = random.uniform(10, 20)
                if method.lower() == "get":
                    resp = session.get(url, timeout=timeout, **kwargs)
                else:
                    resp = session.post(url, timeout=timeout, **kwargs)
                time.sleep(random.uniform(0.5, 3))
                return resp
            except Exception as e:
                if retry < max_retries - 1:
                    wait = random.uniform(5, 10) * (retry + 1)
                    time.sleep(wait)
        return None

    def _get_username(self, session):
        username = "未知用户"
        try:
            resp = self._safe_request(session, "get", f"{self.base_url}home.php?mod=space")
            if resp:
                match = re.search(r'<h2 class="mt"\s*>(.*?)</h2>', resp.text, re.S)
                if match and match.group(1).strip():
                    return match.group(1).strip()
        except:
            try:
                resp = self._safe_request(session, "get", self.base_url)
                if resp:
                    match = re.search(r'欢迎(您回来，|)([^<]{2,20})<', resp.text, re.S)
                    if match:
                        return match.group(2).strip()
            except:
                pass
        return username

    def _get_formhash(self, session):
        try:
            resp = self._safe_request(session, "get", f"{self.base_url}plugin.php?id=proalsupport")
            if resp:
                match = re.search(r'formhash=(.*?)["&]', resp.text)
                if match:
                    return match.group(1)
        except:
            pass
        return None

    def do_sign(self, session, cookie_dict, account_idx):
        time.sleep(random.uniform(*self.sign_delay))
        username = self._get_username(session)
        sign_ip = cookie_dict.get("JoRn_2132_lip", "未知").split(",")[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n===== 账号{account_idx}（{username}）- 签到 =====")

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
                resp = self._safe_request(session, "post", sign_url)
                if resp and ("签到成功" in resp.text or "已签到" in resp.text):
                    success = True
                    break
            except:
                time.sleep(3)

        if success:
            self.user_data["sign_status"][username] = today
            self._save_data()
            result = f"👤 {username}\n📝 签到：成功\n🌐 IP：{sign_ip}\n⏰ {now}"
        else:
            result = f"👤 {username}\n📝 签到：失败\n🌐 IP：{sign_ip}\n⏰ {now}"
        self.results.append(result)
        print(result)
        time.sleep(random.uniform(*self.sign_delay))
        return session

    def _get_activity_posts(self):
        posts = []
        current_ts = time.time()
        for aid in range(self.min_aid, self.max_aid + 1):
            aid_str = str(aid)
            last_ts = self.user_data["commented_records"].get(aid_str, 0)
            if current_ts - last_ts >= self.recomment_interval:
                posts.append({"aid": aid_str, "url": f"{self.base_url}plugin.php?id=proalsupport&modac=post&submodac=detail&aid={aid_str}"})
        random.shuffle(posts)
        print(f"✅ 可评论活动：{len(posts)}个（ID范围{self.min_aid}-{self.max_aid}）")
        return posts

    def do_activity_comments(self, session, username):
        print(f"\n===== {username} - 评论（5天1次，每次1条） =====")
        posts = self._get_activity_posts()
        if not posts:
            self.results.append("📊 评论：暂无符合5天冷却的活动")
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
            current_ts = time.time()
            last_comment_ts = self.user_data["commented_records"].get(aid, 0)
            if current_ts - last_comment_ts < self.recomment_interval:
                continue

            try:
                self._safe_request(session, "get", post["url"])
                time.sleep(random.uniform(*self.page_load_delay))
                content = random.choice(self.comment_content)
                comment_params = {"formhash": formhash, "aid": aid, "content": content}
                interval = random.uniform(*self.comment_interval)
                print(f"⏳ 等待{interval:.1f}秒，评论ID：{aid}")
                time.sleep(interval)

                resp = self._safe_request(session, "post", self.comment_api_url, data=comment_params)
                if not resp:
                    print(f"❌ 评论失败 ID：{aid}")
                    continue

                resp_text = resp.text.strip()
                if "操作频繁" in resp_text or "验证码" in resp_text:
                    print(f"⚠️ 触发风控，暂停3分钟")
                    time.sleep(180)
                    formhash = self._get_formhash(session)
                    continue

                try:
                    resp_json = json.loads(resp_text)
                    if resp_json.get("rs") == 200 and resp_json.get("msg") == "评论成功":
                        comment_count += 1
                        self.user_data["commented_records"][aid] = current_ts
                        self._save_data()
                        print(f"✅ 评论成功：{content}（ID：{aid}）")
                except:
                    print(f"❌ 评论失败 ID：{aid}")
            except Exception as e:
                continue

        self.results.append(f"📊 评论：完成 {comment_count}/1 条（7天冷却）")

    def run(self):
        if not self.cookies:
            print("❌ 未检测到有效Cookie")
            send("富贵论坛任务", "未检测到有效Cookie")
            return

        print(f"✅ 检测到{len(self.cookies)}个账号，启动任务...")
        time.sleep(random.uniform(3, 7))

        for idx, cookie in enumerate(self.cookies, 1):
            session = requests.Session()
            session.headers.update(self.headers)
            cookie_dict = {}
            for item in urllib.parse.unquote(cookie).split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookie_dict[k] = v
            session.cookies.update(cookie_dict)

            login_valid = False
            try:
                resp = self._safe_request(session, "get", self.base_url)
                if resp and "退出" in resp.text:
                    login_valid = True
            except:
                pass

            if not login_valid:
                result = f"👤 未知用户\n❌ Cookie失效"
                self.results.append(result)
                print(result)
                continue

            self.do_sign(session, cookie_dict, idx)
            username = self._get_username(session)
            self.do_activity_comments(session, username)

            if idx < len(self.cookies):
                time.sleep(random.uniform(*self.account_switch_delay))

        notify_content = "\n\n".join(self.results)
        send("富贵论坛任务结果", notify_content)
        print("\n✅ 任务完成！")

if __name__ == "__main__":
    cookies = os.getenv("fg_cookies", "").split("&")
    cookies = [c.strip() for c in cookies if c.strip()]
    if not cookies:
        print("❌ 请设置环境变量 fg_cookies")
        sys.exit(1)
    task = FGLTActivityTask(cookies)
    task.run()
    sys.exit(0)
