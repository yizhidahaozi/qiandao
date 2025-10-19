#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: AcFun_auto_sign.py
Author: Auto-Sign
Date: 2025/10/19
cron: 35 7 * * *  # 建议与MT论坛签到错开时间，避免并发
new Env('AcFun自动签到');
"""
import json
import os
import re
import sys  # 新增：用于处理notify导入失败
import requests
import urllib3

from dailycheckin import CheckIn

# 关键1：导入多渠道通知脚本（与MT论坛脚本一致的通知逻辑）
try:
    from notify import send  # 从notify.py导入核心通知函数
except ImportError:
    print("❌ 未找到通知脚本notify.py，请检查文件路径或文件名！")
    send = None  # 避免后续调用报错，设为None

# 禁用SSL警告 🔒
urllib3.disable_warnings()


class AcFun(CheckIn):
    name = "AcFun 自动签到"  # 📺 平台名称
    def __init__(self, check_item: dict = None):
        self.check_item = check_item or {}
        self.contentid = "27259341"  # 📹 默认视频ID（后续会自动更新）
        self.st = None  # 🔑 接口令牌（用于点赞等操作）

    # 🔐 账号登录验证
    @staticmethod
    def login(phone, password, session):
        url = "https://id.app.acfun.cn/rest/web/login/signin"
        body = f"username={phone}&password={password}&key=&captcha="
        res = session.post(url=url, data=body).json()
        return (True, res) if res.get("result") == 0 else (False, res.get("err_msg", "登录接口无返回"))

    # 🍪 获取登录Cookies
    @staticmethod
    def get_cookies(session, phone, password):
        url = "https://id.app.acfun.cn/rest/app/login/signin"
        headers = {
            "Host": "id.app.acfun.cn",
            "user-agent": "AcFun/6.39.0 (iPhone; iOS 14.3; Scale/2.00)",
            "devicetype": "0",
            "accept-language": "zh-Hans-CN;q=1, en-CN;q=0.9, ja-CN;q=0.8, zh-Hant-HK;q=0.7, io-Latn-CN;q=0.6",
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        }
        data = f"password={password}&username={phone}"
        response = session.post(url=url, data=data, headers=headers, verify=False)
        acpasstoken = response.json().get("acPassToken")
        auth_key = str(response.json().get("auth_key"))
        if acpasstoken and auth_key:
            return {"acPasstoken": acpasstoken, "auth_key": auth_key}  # ✅ 成功获取Cookies
        else:
            return False  # ❌ 失败

    # 🔑 获取接口令牌（st）
    def get_token(self, session):
        url = "https://id.app.acfun.cn/rest/web/token/get?sid=acfun.midground.api"
        res = session.post(url=url).json()
        self.st = res.get("acfun.midground.api_st") if res.get("result") == 0 else ""
        return self.st  # 返回令牌（空则获取失败）

    # 📹 获取热门视频ID（用于弹幕/投香蕉）
    def get_video(self, session):
        url = "https://www.acfun.cn/rest/pc-direct/rank/channel"
        res = session.get(url=url).json()
        self.contentid = res.get("rankList", [{}])[0].get("contentId", "27259341")
        return self.contentid

    # 📅 执行签到操作
    @staticmethod
    def sign(session):
        url = "https://www.acfun.cn/rest/pc-direct/user/signIn"
        response = session.post(url=url).json()
        msg = response.get("msg", "签到接口无响应")
        return {"name": "📅 签到信息", "value": f"✅ {msg}" if response.get("result") == 0 else f"❌ {msg}"}

    # 💬 发送弹幕任务
    def danmu(self, session):
        url = "https://www.acfun.cn/rest/pc-direct/new-danmaku/add"
        data = {
            "mode": "1", "color": "16777215", "size": "25", "body": "123321",
            "videoId": "26113662", "position": "2719", "type": "douga",
            "id": "31224739", "subChannelId": "1", "subChannelName": "动画"
        }
        response = session.get(url=f"https://www.acfun.cn/v/ac{self.contentid}")
        video_id = re.findall(r'"currentVideoId":(\d+),', response.text)
        sub_channel = re.findall(r'{subChannelId:(\d+),subChannelName:"([\u4e00-\u9fa5]+)"}', response.text)
        
        if video_id and sub_channel:
            data["videoId"] = video_id[0]
            data["subChannelId"] = sub_channel[0][0]
            data["subChannelName"] = sub_channel[0][1]
        
        res = session.post(url=url, data=data).json()
        msg = "✅ 弹幕成功" if res.get("result") == 0 else f"❌ 弹幕失败（{res.get('msg', '未知错误')}）"
        return {"name": "💬 弹幕任务", "value": msg}

    # 🍌 投香蕉任务
    def throwbanana(self, session):
        url = "https://www.acfun.cn/rest/pc-direct/banana/throwBanana"
        data = {"resourceId": self.contentid, "count": "1", "resourceType": "2"}
        res = session.post(url=url, data=data).json()
        msg = "✅ 投🍌成功" if res.get("result") == 0 else f"❌ 投🍌失败（{res.get('msg', '未知错误')}）"
        return {"name": "🍌 香蕉任务", "value": msg}

    # 👍 点赞+取消点赞任务
    def like(self, session):
        if not self.st:
            return {"name": "👍 点赞任务", "value": "❌ 令牌未获取，无法点赞"}
        
        like_url = "https://kuaishouzt.com/rest/zt/interact/add"
        unlike_url = "https://kuaishouzt.com/rest/zt/interact/delete"
        body = (
            f"kpn=ACFUN_APP&kpf=PC_WEB&subBiz=mainApp&interactType=1&"
            f"objectType=2&objectId={self.contentid}&acfun.midground.api_st={self.st}&"
            f"extParams%5BisPlaying%5D=false&extParams%5BshowCount%5D=1&"
            f"extParams%5BotherBtnClickedCount%5D=10&extParams%5BplayBtnClickedCount%5D=0"
        )
        
        res = session.post(url=like_url, data=body).json()
        session.post(url=unlike_url, data=body)
        msg = "✅ 点赞成功" if res.get("result") == 1 else f"❌ 点赞失败（{res.get('error_msg', '未知错误')}）"
        return {"name": "👍 点赞任务", "value": msg}

    # 📤 分享任务
    def share(self, session, cookies):
        url = "https://api-ipv6.acfunchina.com/rest/app/task/reportTaskAction?taskType=1&market=tencent&product=ACFUN_APP&appMode=0"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = session.get(url=url, headers=headers, cookies=cookies, verify=False).json()
        msg = "✅ 分享成功" if response.get("result") == 0 else f"❌ 分享失败（{response.get('msg', '未知错误')}）"
        return {"name": "📤 分享任务", "value": msg}

    # ℹ️ 获取账号基本信息
    @staticmethod
    def get_info(session):
        url = "https://www.acfun.cn/rest/pc-direct/user/personalInfo"
        res = session.get(url=url).json()
        if res.get("result") != 0:
            return [{"name": "ℹ️ 当前等级", "value": "❌ 查询失败"}, {"name": "🍌 持有香蕉", "value": "❌ 查询失败"}]
        
        info = res.get("info", {})
        return [
            {"name": "ℹ️ 当前等级", "value": f"✅ {info.get('level', '未知')}"},
            {"name": "🍌 持有香蕉", "value": f"✅ {info.get('banana', 0)} 个"}
        ]

    # 🚀 主执行逻辑
    def main(self):
        # --------------------------
        # 📱 账号配置（二选一）
        # --------------------------
        DEFAULT_PHONE = ""  # 直接填手机号（例："13800138000"）
        DEFAULT_PASSWORD = ""  # 直接填密码（例："your_password123"）

        # 优先级：环境变量 > 代码内默认值
        phone = os.getenv("ACFUN_PHONE", DEFAULT_PHONE)
        password = os.getenv("ACFUN_PASSWORD", DEFAULT_PASSWORD)

        if not phone or not password:
            return "⚠️ 错误：请设置环境变量【ACFUN_PHONE】【ACFUN_PASSWORD】，或在代码内填写默认值"

        session = requests.session()
        session.headers。update({
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.70",
            "Referer": "https://www.acfun.cn/",
        })

        # 执行登录
        flag, res = self.login(phone, password, session)
        if flag:
            self.get_video(session)
            self.get_token(session)
            cookies = self.get_cookies(session, phone, password)
            
            sign_msg = self.sign(session)
            like_msg = self.like(session)
            danmu_msg = self.danmu(session)
            throwbanana_msg = self.throwbanana(session)
            share_msg = self.share(session, cookies) if cookies else {"name": "📤 分享任务", "value": "❌ Cookies获取失败"}
            info_msg = self.get_info(session)

            msg_list = [
                {"name": "📱 账号信息", "value": phone}，
                sign_msg, like_msg, danmu_msg, throwbanana_msg, share_msg,
                *info_msg
            ]
        else:
            msg_list = [
                {"name": "📱 账号信息", "value": phone},
                {"name": "⚠️ 错误信息", "value": f"登录失败：{res}"}
            ]

        # 格式化输出结果（与MT论坛脚本通知格式一致）
        return "\n"。join([f"{item['name']}: {item['value']}" for item in msg_list])


if __name__ == "__main__":
    print("=" * 40)
    print("📺 AcFun 自动签到脚本开始执行")
    print("=" * 40)
    
    # 执行签到并获取结果
    acfun_sign = AcFun()
    final_result = acfun_sign.main()
    print(final_result)  # 本地打印结果
    
    print("=" * 40)
    print("📺 执行结束")
    print("=" * 40)

    # 关键2：调用多渠道通知（若notify导入成功）
    if send:
        print("\n📤 正在发送通知...")
        send(
            title="AcFun自动签到结果",  # 通知标题（与脚本功能匹配）
            content=final_result       # 通知内容（完整签到结果）
        )
        print("✅ 通知发送完成（具体以notify配置渠道为准）")
    else:
        print("\n❌ 通知功能不可用（未找到notify.py）")
