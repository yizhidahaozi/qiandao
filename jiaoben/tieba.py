#!/usr/bin/python3
# -- coding: utf-8 --
# -------------------------------
# 百度贴吧签到 终极编码修复版
# -------------------------------
# cron "15 20 6,15 * * *" script-path=xxx.py
# const $ = new Env('百度贴吧')

import hashlib
import re
import os
import json
import requests
from datetime import datetime

# 全局禁用严格编码
import sys
import warnings
warnings.filterwarnings("ignore")
reload(sys) if 'reload' in dir() else None
sys.setdefaultencoding('utf-8') if hasattr(sys, 'setdefaultencoding') else None


class Notifier:
    def __init__(self, push_token, ql_url, ql_token):
        self.push_token = push_token
        self.ql_url = ql_url
        self.ql_token = ql_token

    def _format_content(self, content):
        if isinstance(content, dict):
            content["时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return json.dumps(content, ensure_ascii=False, indent=2)
        return content

    def push_plus(self, title, content):
        if not self.push_token:
            return None
        try:
            res = requests.post("https://www.pushplus.plus/send", json={
                "token": self.push_token, "title": title,
                "content": self._format_content(content), "template": "json"
            }, timeout=10)
            return "✅ PushPlus通知成功" if res.json().get("code") == 200 else "❌ PushPlus失败"
        except:
            return "❌ PushPlus异常"

    def qinglong(self, title, content):
        if not self.ql_url or not self.ql_token:
            return None
        try:
            res = requests.post(f"{self.ql_url}/open/system/notify",
                headers={"Authorization": f"Bearer {self.ql_token}"},
                json={"title": title, "content": self._format_content(content)}, timeout=10)
            return "✅ 青龙通知成功" if res.json().get("code") == 200 else "❌ 青龙失败"
        except:
            return "❌ 青龙异常"

    def send(self, title, content):
        r = []
        p = self.push_plus(title, content)
        q = self.qinglong(title, content)
        if p: r.append(p)
        if q: r.append(q)
        if r: print("📢 通知结果: " + "; ".join(r))


class Tieba:
    def __init__(self, cookie_str, notifier):
        self.cookie_raw = cookie_str
        self.notifier = notifier
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.baidu.com/",
            "Cookie": self.clean_cookie()  # ✅ 直接用Header传Cookie，彻底避开编码坑
        })

    def clean_cookie(self):
        # ✅ 终极清洗：过滤所有非ASCII乱码
        c = self.cookie_raw
        c = re.sub(r'[^\x00-\x7F]+', '', c)
        c = re.sub(r'baidu_broswer_setup[^;]*;?', '', c)
        c = re.sub(r'\s+', ' ', c).strip()
        return c

    def get_tbs(self):
        try:
            res = self.s.get("http://tieba.baidu.com/dc/common/tbs", timeout=8).json()
            if res.get("is_login") == 1:
                return res.get("tbs")
        except:
            return None

    def get_like_tiebas(self):
        try:
            r = self.s.get("https://tieba.baidu.com/f/like/mylike?pn=1", timeout=10)
            txt = r.text
            pages = 1
            m = re.search(r'pn=(\d+)">尾页', txt)
            if m: pages = int(m.group(1))
            names = []
            pat = re.compile(r'title="([^"]+?)"', re.S)
            for p in range(1, pages+1):
                if p>1: r = self.s.get(f"https://tieba.baidu.com/f/like/mylike?pn={p}", timeout=10)
                names += pat.findall(r.text)
            return list(set(names))
        except:
            return []

    def sign(self, kw, tbs):
        try:
            s = f"kw={kw}tbs={tbs}tiebaclient!!!"
            sign = hashlib.md5(s.encode()).hexdigest()
            r = self.s.post("http://c.tieba.baidu.com/c/c/forum/sign",
                data={"kw":kw,"tbs":tbs,"sign":sign}, timeout=8)
            return r.json().get("error_code")
        except:
            return "err"

    def run(self):
        tbs = self.get_tbs()
        if not tbs:
            return "❌ 登录失效：Cookie已过期或异常"

        tiebas = self.get_like_tiebas()
        if not tiebas:
            return "✅ 无关注贴吧"

        ok = exist = shield = fail = 0
        for tb in tiebas:
            code = self.sign(tb, tbs)
            if code == "0": ok +=1
            elif code == "160002": exist +=1
            elif code == "340006": shield +=1
            else: fail +=1

        return (
            f"✅ 签到完成\n"
            f"总数：{len(tiebas)}\n"
            f"成功：{ok}\n"
            f"已签：{exist}\n"
            f"屏蔽：{shield}\n"
            f"失败：{fail}"
        )


def start():
    notifier = Notifier(
        push_token=os.environ.get("PUSH_PLUS_TOKEN",""),
        ql_url=os.environ.get("QL_API_URL",""),
        ql_token=os.environ.get("QL_API_TOKEN","")
    )

    tieback = os.getenv("tieback")
    if not tieback:
        print("❌ 未配置 tieback")
        notifier.send("贴吧签到错误", "未配置Cookie")
        return

    accounts = tieback.split("#")
    print(f"👥 共 {len(accounts)} 个账号")

    final = ""
    for idx, ck in enumerate(accounts, 1):
        if not ck.strip(): continue
        print(f"\n=== 正在签到第 {idx} 个账号 ===")
        tb = Tieba(ck.strip(), notifier)
        res = tb.run()
        final += f"【账号{idx}】\n{res}\n\n"
        notifier.send(f"贴吧签到 {idx}", res)

    print("\n====== 最终结果 ======")
    print(final)


if __name__ == "__main__":
    start()
