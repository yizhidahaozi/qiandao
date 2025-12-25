#!/usr/bin/python3
# 来自https://github.com/wd210010/only_for_happly/blob/main/kuake.py
# 二次修改时间：2025年11月10日18点30分（每日评论量调整为5-16条随机）
# -- coding: utf-8 --
# -------------------------------
# @功能：富贵论坛签到+固定范围活动评论（250-1219）
# @核心：ID区间遍历+时间戳去重+评论数量随机控制
# 在259行修改范围 print(f"✅ 生成可评论活动：{len(posts)}个（ID范围250-1219）")
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
        
        # 2. 数据存储（防重复：记录评论时间戳）
        self.data_file = "fgl_activity_comment.json"
        self.user_data = {
            "sign_status": {},
            "commented_records": {}  # 格式：{活动ID: 上次评论时间戳（秒）}
        }
        self._load_data()
        self.recomment_interval = 86400  # 24小时重复评论间隔（秒）
        
        # 3. 评论配置（核心修改：每日5-16条随机评论）
        self.min_comment = 5         # 最低评论数
        self.max_comment = 16        # 最高评论数（限制最多16条）
        self.daily_comment = random.randint(self.min_comment, self.max_comment)  # 每日随机数量
        self.comment_interval = (60, 120)  # 评论间隔：60-120秒
        self.sign_delay = (3, 8)  # 签到前后延迟
        self.account_switch_delay = (30, 60)  # 账号切换延迟
        self.page_load_delay = (2, 5)  # 页面浏览延迟
        # 固定评论内容
        self.comment_content = [
            "支持富贵",
            "支持富贵越来越好！！！",
            "支持 富贵有你更精彩"
        ]
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
        """构造接近真人的请求头（防反爬）"""
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
        random_aid = random.randint(self.min_aid, self.max_aid)
        return {
            "Host": "www.fglt.net",
            "Origin": "https://www.fglt.net",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": f"{self.base_url}plugin.php?id=proalsupport&modac=post&submodac=detail&aid={random_aid}",
            "User-Agent": random.choice(user_agents),
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": random.choice(accept_languages),
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }

    def _load_data(self):
        """加载历史数据（兼容旧格式）"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.user_data["sign_status"] = loaded.get("sign_status", {})
                    # 兼容旧版本的已评论ID集合
                    old_records = loaded.get("commented_aids", {})
                    if isinstance(old_records, list):
                        self.user_data["commented_records"] = {aid: 0 for aid in old_records}
                    else:
                        self.user_data["commented_records"] = loaded.get("commented_records", {})
                print(f"✅ 加载历史数据：已评论{len(self.user_data['commented_records'])}个活动")
        except Exception as e:
            print(f"⚠️ 加载数据失败：{str(e)}")

    def _save_data(self):
        """保存评论记录（含时间戳）"""
        try:
            save_data = {
                "sign_status": self.user_data["sign_status"],
                "commented_records": self.user_data["commented_records"]
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存数据失败：{str(e)}")

    # 安全请求封装（带重试）
    def _safe_request(self, session, method, url, **kwargs):
        max_retries = 3
        for retry in range(max_retries):
            try:
                timeout = random.uniform(10, 20)
                if method.lower() == "get":
                    resp = session.get(url, timeout=timeout,** kwargs)
                else:
                    resp = session.post(url, timeout=timeout, **kwargs)
                time.sleep(random.uniform(0.5, min(3, len(resp.content)/1024/10)))
                return resp
            except Exception as e:
                if retry < max_retries - 1:
                    wait = random.uniform(5, 10) * (retry + 1)
                    print(f"⚠️ 请求失败（{retry+1}/{max_retries}），{wait:.1f}秒后重试")
                    time.sleep(wait)
        return None

    # ------------------------------
    # 签到功能
    # ------------------------------
    def _get_username(self, session):
        """提取用户名"""
        username = "未知用户"
        try:
            resp = self._safe_request(session, "get", f"{self.base_url}home.php?mod=space")
            if resp:
                match = re.search(r'<h2 class="mt"\s*>(.*?)</h2>', resp.text, re.S)
                if match and match.group(1).strip():
                    username = match.group(1).strip()
                    return username
        except:
            try:
                resp = self._safe_request(session, "get", self.base_url)
                if resp:
                    match = re.search(r'欢迎(您回来，|)([^<]{2,20})<', resp.text, re.S)
                    if match:
                        username = match.group(2).strip()
            except:
                pass
        return username

    def _get_formhash(self, session):
        """获取formhash参数"""
        try:
            resp = self._safe_request(session, "get", f"{self.base_url}plugin.php?id=proalsupport")
            if resp:
                match = re.search(r'formhash=(.*?)["&]', resp.text)
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"❌ 获取formhash失败：{str(e)}")
        return None

    def do_sign(self, session, cookie_dict, account_idx):
        """执行签到"""
        time.sleep(random.uniform(*self.sign_delay))  # 签到前延迟
        username = self._get_username(session)
        sign_ip = cookie_dict.get("JoRn_2132_lip", "未知").split(",")[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n===== 账号{account_idx}（{username}）- 签到任务 =====")

        # 检查今日是否已签到
        if username in self.user_data["sign_status"] and self.user_data["sign_status"][username] == today:
            result = f"👤 {username}\n📝 签到：今日已完成\n🌐 IP：{sign_ip}\n⏰ {now}"
            self.results.append(result)
            print(result)
            time.sleep(random.uniform(*self.sign_delay))
            return session

        formhash = self._get_formhash(session)
        if not formhash:
            result = f"👤 {username}\n📝 签到：失败（无formhash）\n🌐 IP：{sign_ip}\n⏰ {now}"
            self.results.append(result)
            print(result)
            time.sleep(random.uniform(*self.sign_delay))
            return session

        # 执行签到请求
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

        # 处理签到结果
        if success:
            self.user_data["sign_status"][username] = today
            self._save_data()
            result = f"👤 {username}\n📝 签到：成功（+1经验）\n🌐 IP：{sign_ip}\n⏰ {now}"
        else:
            result = f"👤 {username}\n📝 签到：失败（响应异常）\n🌐 IP：{sign_ip}\n⏰ {now}"
        self.results.append(result)
        print(result)
        time.sleep(random.uniform(*self.sign_delay))  # 签到后延迟
        return session

    # ------------------------------
    # 活动评论功能（核心）
    # ------------------------------
    def _get_activity_posts(self):
        """生成未评论活动列表（随机排序）"""
        posts = []
        for aid in range(self.max_aid, self.min_aid - 1, -1):
            aid_str = str(aid)
            # 仅加入未评论或已超过评论间隔的活动
            current_ts = time.time()
            last_ts = self.user_data["commented_records"].get(aid_str, 0)
            if current_ts - last_ts >= self.recomment_interval:
                posts.append({
                    "aid": aid_str,
                    "url": f"{self.base_url}plugin.php?id=proalsupport&modac=post&submodac=detail&aid={aid_str}"
                })
        # 随机打乱顺序，模拟真人浏览
        random.shuffle(posts)
        print(f"✅ 生成可评论活动：{len(posts)}个（ID范围250-1219）")
        return posts

    def do_activity_comments(self, session, username):
        """执行评论（每日5-16条随机）"""
        print(f"\n===== {username} - 评论任务（今日{self.daily_comment}条） =====")
        posts = self._get_activity_posts()
        if not posts:
            self.results.append("📊 评论：250-1219范围已无符合条件的活动（24小时内均已评论）")
            return

        comment_count = 0
        formhash = self._get_formhash(session)
        if not formhash:
            self.results.append("📊 评论：失败（无法获取formhash）")
            return

        for post in posts:
            if comment_count >= self.daily_comment:
                break  # 达到今日随机数量则停止

            aid = post["aid"]
            current_ts = time.time()
            last_comment_ts = self.user_data["commented_records"].get(aid, 0)

            # 24小时间隔校验（双重保险）
            if current_ts - last_comment_ts < self.recomment_interval:
                remaining_hours = (self.recomment_interval - (current_ts - last_comment_ts)) / 3600
                print(f"⚠️ 跳过ID：{aid}（距离上次评论仅{remaining_hours:.1f}小时，需间隔24小时）")
                continue

            try:
                # 先浏览活动页面（模拟真人行为）
                self._safe_request(session, "get", post["url"])
                time.sleep(random.uniform(*self.page_load_delay))

                # 随机选择评论内容
                content = random.choice(self.comment_content)
                comment_params = {
                    "formhash": formhash,
                    "aid": aid,
                    "content": content
                }

                # 评论间隔等待
                interval = random.uniform(*self.comment_interval)
                print(f"⏳ 等待{interval:.1f}秒，评论ID：{aid}...")
                time.sleep(interval)

                # 发送评论请求
                resp = self._safe_request(session, "post", self.comment_api_url, data=comment_params)
                if not resp:
                    print(f"❌ 评论请求失败（ID：{aid}）")
                    continue

                resp_text = resp.text.strip()
                # 检测反爬信号
                if "操作频繁" in resp_text or "请稍后再试" in resp_text or "验证码" in resp_text:
                    print(f"⚠️ 触发反爬机制，暂停3-5分钟...")
                    time.sleep(random.uniform(180, 300))
                    formhash = self._get_formhash(session)  # 重新获取formhash
                    if not formhash:
                        break
                    continue

                # 解析评论结果
                try:
                    resp_json = json.loads(resp_text)
                    if resp_json.get("rs") == 200 and resp_json.get("msg") == "评论成功":
                        comment_count += 1
                        self.user_data["commented_records"][aid] = current_ts  # 记录当前时间戳
                        self._save_data()  # 立即保存，防止重复
                        print(f"✅ 评论{comment_count}/{self.daily_comment}：{content}（ID：{aid}）")
                    else:
                        print(f"❌ 评论失败（ID：{aid}）：{resp_json.get('msg', '未知错误')}")
                except json.JSONDecodeError:
                    print(f"❌ 响应格式异常（ID：{aid}）：{resp_text[:50]}")
            except Exception as e:
                print(f"❌ 评论出错（ID：{aid}）：{str(e)}")
                continue

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
                resp = self._safe_request(session, "get", self.base_url)
                if resp and "退出" in resp.text:
                    login_valid = True
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
                time.sleep(random.uniform(*self.account_switch_delay))

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
