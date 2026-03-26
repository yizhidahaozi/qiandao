#!/usr/bin/env python3
#修改时间2025年10月19日17:23
#源码来自基于「Docker」/「青龙面板」/「群晖」的每日签到脚本（支持多账号）签到列表: ｜爱奇艺｜全民K歌｜有道云笔记｜百度贴吧｜Bilibili｜V2EX｜AcFun｜什么值得买｜阿里云盘｜i茅台申购｜小米运动｜百度搜索资源平台｜恩山论坛｜奥拉星｜ ：https://github.com/Sitoi/dailycheckin.git

# -*- coding: utf-8 -*-
"""
File: AcFun_auto_sign.py
Author: Auto-Sign
Date: 2025/10/19
cron: 05 7 * * *
new Env('AcFun自动签到');
"""
import json
import os
import re
import sys
import requests
import urllib3

from dailycheckin import CheckIn

# 导入多渠道通知
try:
    from notify import send
except ImportError:
    print("❌ 未找到notify.py，通知功能禁用")
    send = None

# 禁用SSL警告
urllib3.disable_warnings()


class AcFun(CheckIn):
    name = "AcFun 自动签到"
    def __init__(self, check_item: dict = None):
        self.check_item = check_item or {}
        self.contentid = "27259341"
        self.st = None

    # 登录验证（保持session登录状态）
    @staticmethod
    def login(phone, password, session):
        url = "https://id.app.acfun.cn/rest/web/login/signin"
        body = f"username={phone}&password={password}&key=&captcha="
        try:
            res = session.post(url=url, data=body, timeout=15).json()
            if res.get("result") == 0:
                print("✅ 登录成功，session已保留登录状态")
                return (True, res)
            else:
                return (False, res.get("err_msg", "登录失败"))
        except Exception as e:
            return (False, f"登录接口异常：{str(e)}")

    # 优化：从session中提取Cookies（替代单独接口调用）
    @staticmethod
    def get_cookies_from_session(session):
        """从登录后的session中直接提取所需Cookies（acPasstoken和auth_key）"""
        try:
            # 从session的cookies中提取字段
            acpasstoken = session.cookies.get("acPasstoken", "")
            auth_key = session.cookies.get("auth_key", "")
            
            if acpasstoken and auth_key:
                print("✅ 从session中成功提取Cookies")
                return {"acPasstoken": acpasstoken, "auth_key": auth_key}
            else:
                print(f"❌ session中Cookies不完整（acPasstoken: {bool(acpasstoken)}, auth_key: {bool(auth_key)}）")
                return False
        except Exception as e:
            print(f"❌ 提取session中Cookies异常：{str(e)}")
            return False

    # 获取接口令牌
    def get_token(self, session):
        url = "https://id.app.acfun.cn/rest/web/token/get?sid=acfun.midground.api"
        try:
            res = session.post(url=url, timeout=15).json()
            self.st = res.get("acfun.midground.api_st") if res.get("result") == 0 else ""
            return self.st
        except Exception as e:
            print(f"❌ 获取令牌异常：{str(e)}")
            self.st = ""
            return ""

    # 获取热门视频ID
    def get_video(self, session):
        url = "https://www.acfun.cn/rest/pc-direct/rank/channel"
        try:
            res = session.get(url=url, timeout=15).json()
            self.contentid = res.get("rankList", [{}])[0].get("contentId", "27259341")
            print(f"🎬 获取热门视频ID：{self.contentid}")
            return self.contentid
        except Exception as e:
            print(f"❌ 获取视频ID异常：{str(e)}")
            return self.contentid

    # 签到操作
    @staticmethod
    def sign(session):
        url = "https://www.acfun.cn/rest/pc-direct/user/signIn"
        try:
            response = session.post(url=url, timeout=15).json()
            msg = response.get("msg", "未知结果")
            return {"name": "📅 签到信息", "value": f"✅ {msg}" if response.get("result") == 0 else f"❌ {msg}"}
        except Exception as e:
            return {"name": "📅 签到信息", "value": f"❌ 接口异常：{str(e)}"}

    # 弹幕任务
    def danmu(self, session):
        url = "https://www.acfun.cn/rest/pc-direct/new-danmaku/add"
        data = {
            "mode": "1", "color": "16777215", "size": "25", "body": "自动签到弹幕~",
            "videoId": "26113662", "position": "2719", "type": "douga",
            "id": "31224739", "subChannelId": "1", "subChannelName": "动画"
        }
        try:
            response = session.get(url=f"https://www.acfun.cn/v/ac{self.contentid}", timeout=15)
            video_id = re.findall(r'"currentVideoId":(\d+),', response.text)
            sub_channel = re.findall(r'{subChannelId:(\d+),subChannelName:"([\u4e00-\u9fa5]+)"}', response.text)
            
            if video_id and sub_channel:
                data["videoId"] = video_id[0]
                data["subChannelId"] = sub_channel[0][0]
                data["subChannelName"] = sub_channel[0][1]
            
            res = session.post(url=url, data=data, timeout=15).json()
            msg = "✅ 弹幕成功" if res.get("result") == 0 else f"❌ 弹幕失败（{res.get('msg', '未知错误')}）"
            return {"name": "💬 弹幕任务", "value": msg}
        except Exception as e:
            return {"name": "💬 弹幕任务", "value": f"❌ 异常：{str(e)}"}

    # 投香蕉任务
    def throwbanana(self, session):
        url = "https://www.acfun.cn/rest/pc-direct/banana/throwBanana"
        data = {"resourceId": self.contentid, "count": "1", "resourceType": "2"}
        try:
            res = session.post(url=url, data=data, timeout=15).json()
            msg = "✅ 投🍌成功" if res.get("result") == 0 else f"❌ 投🍌失败（{res.get('msg', '未知错误')}）"
            return {"name": "🍌 香蕉任务", "value": msg}
        except Exception as e:
            return {"name": "🍌 香蕉任务", "value": f"❌ 异常：{str(e)}"}

    # 点赞任务
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
        try:
            res = session.post(url=like_url, data=body, timeout=15).json()
            session.post(url=unlike_url, data=body, timeout=15)
            msg = "✅ 点赞成功" if res.get("result") == 1 else f"❌ 点赞失败（{res.get('error_msg', '未知错误')}）"
            return {"name": "👍 点赞任务", "value": msg}
        except Exception as e:
            return {"name": "👍 点赞任务", "value": f"❌ 异常：{str(e)}"}

    # 分享任务（依赖session提取的Cookies）
    def share(self, session, cookies):
        if not cookies:
            return {"name": "📤 分享任务", "value": "❌ 缺少Cookies（未获取到登录状态）"}
        
        url = "https://api-ipv6.acfunchina.com/rest/app/task/reportTaskAction?taskType=1&market=tencent&product=ACFUN_APP&appMode=0"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = session.get(
                url=url, 
                headers=headers, 
                cookies=cookies, 
                verify=False, 
                timeout=15
            ).json()
            msg = "✅ 分享成功" if response.get("result") == 0 else f"❌ 分享失败（{response.get('msg', '未知错误')}）"
            return {"name": "📤 分享任务", "value": msg}
        except Exception as e:
            return {"name": "📤 分享任务", "value": f"❌ 异常：{str(e)}"}

    # 获取账号信息
    @staticmethod
    def get_info(session):
        url = "https://www.acfun.cn/rest/pc-direct/user/personalInfo"
        try:
            res = session.get(url=url, timeout=15).json()
            if res.get("result") != 0:
                return [
                    {"name": "ℹ️ 当前等级", "value": "❌ 查询失败"},
                    {"name": "🍌 持有香蕉", "value": "❌ 查询失败"}
                ]
            
            info = res.get("info", {})
            return [
                {"name": "ℹ️ 当前等级", "value": f"✅ {info.get('level', '未知')}"},
                {"name": "🍌 持有香蕉", "value": f"✅ {info.get('banana', 0)} 个"}
            ]
        except Exception as e:
            return [
                {"name": "ℹ️ 当前等级", "value": f"❌ 异常：{str(e)}"},
                {"name": "🍌 持有香蕉", "value": f"❌ 异常：{str(e)}"}
            ]

    # 主执行逻辑
    def main(self):
        # 账号配置：请替换为你的手机号和密码
        DEFAULT_PHONE = "你的手机号"  # 直接填写手机号
        DEFAULT_PASSWORD = "你的密码"  # 直接填写密码

        phone = os.getenv("ACFUN_PHONE", DEFAULT_PHONE)
        password = os.getenv("ACFUN_PASSWORD", DEFAULT_PASSWORD)

        if not phone or not password:
            return "⚠️ 错误：请设置环境变量【ACFUN_PHONE】【ACFUN_PASSWORD】或代码内填写默认值"

        session = requests.session()
        session.headers.update({
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://www.acfun.cn/",
        })

        # 执行登录（session会自动保留登录状态）
        flag, res = self.login(phone, password, session)
        if flag:
            self.get_video(session)
            self.get_token(session)
            # 从session中提取Cookies（替代原get_cookies方法）
            cookies = self.get_cookies_from_session(session)
            
            # 执行所有任务
            sign_msg = self.sign(session)
            like_msg = self.like(session)
            danmu_msg = self.danmu(session)
            throwbanana_msg = self.throwbanana(session)
            share_msg = self.share(session, cookies)
            info_msg = self.get_info(session)

            msg_list = [
                {"name": "📱 账号信息", "value": phone},
                sign_msg, like_msg, danmu_msg, throwbanana_msg, share_msg,
                *info_msg
            ]
        else:
            msg_list = [
                {"name": "📱 账号信息", "value": phone},
                {"name": "⚠️ 错误信息", "value": f"登录失败：{res}"}
            ]

        # 修复：将中文句号“。”改为英文句号“.”
        return "\n".join([f"{item['name']}: {item['value']}" for item in msg_list])


if __name__ == "__main__":
    print("=" * 40)
    print("📺 AcFun 自动签到脚本开始执行")
    print("=" * 40)
    
    final_result = AcFun().main()
    print(final_result)
    
    print("=" * 40)
    print("📺 执行结束")
    print("=" * 40)

    # 发送通知
    if send:
        print("\n📤 正在发送通知...")
        send("AcFun自动签到结果", final_result)
        print("✅ 通知发送完成")
    else:
        print("\n❌ 通知功能未启用（缺少notify.py）")
