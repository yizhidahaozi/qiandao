#!/usr/bin/python3
# -- coding: utf-8 -- 
# -------------------------------
#修改时间：2025年10月21日16点11分
# @Author : github@wd210010 https://github.com/wd210010/only_for_happly  /https://github.com/wd210010/only_for_happly/blob/main/tieba.py
# 整合通知功能：支持PushPlus和青龙面板通知（无冗余提醒版本）
# -------------------------------
# cron "15 20 6,15 * * *" script-path=xxx.py,tag=匹配cron用
# const $ = new Env('百度贴吧')

import hashlib
import re
import os
import json
import requests
from datetime import datetime


class Notifier:
    """📱 通知工具类（精简输出，去除冗余提醒）"""
    
    def __init__(self, push_token, ql_url, ql_token):
        self.push_token = push_token
        self.ql_url = ql_url
        self.ql_token = ql_token
        
    def _format_content(self, title, content):
        """📝 格式化通知内容为JSON格式"""
        if isinstance(content, dict):
            content["时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return json.dumps(content, ensure_ascii=False, indent=2)
        return content
        
    def push_plus(self, title, content):
        """📲 PushPlus通知发送（无配置时静默跳过）"""
        if not self.push_token:
            return None  # 不返回提示信息
            
        try:
            formatted_content = self._format_content(title, content)
            response = requests.post(
                "https://www.pushplus.plus/send",
                json={
                    "token": self.push_token,
                    "title": title,
                    "content": formatted_content,
                    "template": "json"
                },
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 200:
                return "✅ PushPlus通知成功"
            else:
                return f"❌ PushPlus通知失败: {result.get('msg', '未知错误')}"
                
        except Exception as e:
            return f"❌ PushPlus通知异常: {str(e)}"
    
    def qinglong(self, title, content):
        """🐉 青龙面板通知发送（无配置时静默跳过）"""
        if not self.ql_url or not self.ql_token:
            return None  # 不返回提示信息
            
        try:
            formatted_content = self._format_content(title, content)
            response = requests.post(
                f"{self.ql_url}/open/system/notify",
                headers={"Authorization": f"Bearer {self.ql_token}"},
                json={"title": title, "content": formatted_content},
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 200:
                return "✅ 青龙通知成功"
            else:
                return f"❌ 青龙通知失败: {result.get('message', '未知错误')}"
                
        except Exception as e:
            return f"❌ 青龙通知异常: {str(e)}"
    
    def send(self, title, content, level="info"):
        """📤 发送组合通知（只输出实际结果）"""
        results = []
        
        # 发送PushPlus通知
        push_result = self.push_plus(title, content)
        if push_result:
            results.append(push_result)
        
        # 发送青龙通知
        ql_result = self.qinglong(title, content)
        if ql_result:
            results.append(ql_result)
        
        # 输出非空结果
        if results:
            print(f"📢 通知结果: {'; '.join(results)}")
        return {"push_plus": push_result, "qinglong": ql_result}


class Tieba:
    def __init__(self, check_items, notifier):
        self.check_items = check_items
        self.notifier = notifier
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Referer": "https://www.baidu.com/"
        })

    @staticmethod
    def login_info(session):
        """🔍 获取登录用户信息"""
        try:
            response = session.get("https://zhidao.baidu.com/api/loginInfo", timeout=10)
            return response.json()
        except Exception as e:
            return {"error": f"❌ 获取用户信息失败: {str(e)}"}

    def valid(self):
        """🔐 验证登录状态并获取TBS"""
        try:
            response = self.session.get("http://tieba.baidu.com/dc/common/tbs", timeout=10)
            res = response.json()
            if res.get("is_login") == 0:
                return False, "❌ 登录失败，Cookie异常"
            
            tbs = res.get("tbs")
            user_info = self.login_info(self.session)
            user_name = user_info.get("userName", "未知用户")
            return tbs, f"👤 {user_name}"  # 用户名前加用户表情
            
        except Exception as e:
            return False, f"❌ 验证异常: {str(e)}"

    def get_tieba_list(self):
        """📋 获取关注的贴吧列表"""
        tieba_list = []
        try:
            # 获取第一页内容
            response = self.session.get(
                "https://tieba.baidu.com/f/like/mylike?&pn=1",
                timeout=(5, 20),
                allow_redirects=False
            )
            response.raise_for_status()
            html = response.text
            
            # 解析总页数
            try:
                pn_match = re.search(r'/f/like/mylike\?&pn=(\d+)">尾页', html, re.S | re.I)
                total_pages = int(pn_match.group(1)) if pn_match else 1
            except Exception:
                total_pages = 1
            
            # 提取贴吧名称的正则
            pattern = re.compile(r'<a href="/f\?kw=.*?title="(.*?)">', re.S)
            
            # 处理所有页面
            for page in range(1, total_pages + 1):
                if page > 1:
                    # 获取后续页面
                    response = self.session.get(
                        f"https://tieba.baidu.com/f/like/mylike?&pn={page}",
                        timeout=(5, 20),
                        allow_redirects=False
                    )
                    response.raise_for_status()
                    html = response.text
                
                # 提取当前页贴吧
                tieba_names = pattern.findall(html)
                tieba_list.extend(tieba_names)
            
            return list(set(tieba_list))  # 去重
            
        except Exception as e:
            print(f"❌ 获取贴吧列表失败: {str(e)}")
            return tieba_list

    def sign(self, tb_name_list, tbs):
        """📝 执行贴吧签到"""
        success_count = error_count = exist_count = shield_count = 0
        
        for tb_name in tb_name_list:
            try:
                # 生成签名
                sign_str = f"kw={tb_name}tbs={tbs}tiebaclient!!!"
                sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()
                
                # 发送签到请求
                response = self.session.post(
                    "http://c.tieba.baidu.com/c/c/forum/sign",
                    data={"kw": tb_name, "tbs": tbs, "sign": sign},
                    timeout=10
                )
                res = response.json()
                error_code = res.get("error_code", "")
                
                # 统计结果（匹配对应表情）
                if error_code == "0":
                    success_count += 1  # ✅ 签到成功
                elif error_code == "160002":
                    exist_count += 1    # ℹ️ 已签到
                elif error_code == "340006":
                    shield_count += 1   # 🚫 被屏蔽
                else:
                    error_count += 1    # ❌ 签到失败
                    
            except Exception as e:
                print(f"❌ 贴吧「{tb_name}」签到异常: {str(e)}")
                error_count += 1
        
        return (success_count, error_count, exist_count, shield_count, len(tb_name_list))

    def main(self):
        """🚀 主执行方法"""
        msg_all = ""
        for check_item in self.check_items:
            # 更新当前账号Cookie
            cookie_str = check_item.get("cookie", "")
            cookie_dict = {
                item.split("=", 1)[0]: item.split("=", 1)[1]
                for item in cookie_str.split("; ")
                if "=" in item
            }
            self.session.cookies.clear()
            self.session.cookies.update(cookie_dict)
            
            # 验证登录状态
            tbs, user_name = self.valid()
            
            if tbs:
                # 获取贴吧列表并签到
                tb_list = self.get_tieba_list()
                if not tb_list:
                    msg = f"{user_name}\n📭 提示: 未关注任何贴吧"
                    msg_all += msg + "\n\n"
                    self.notifier.send(
                        title=f"百度贴吧签到通知 - {user_name}",
                        content={"状态": "ℹ️ 无操作", "原因": "未关注任何贴吧", "账号": user_name}
                    )
                    continue
                
                # 执行签到
                success, error, exist, shield, total = self.sign(tb_list, tbs)
                
                # 构建结果信息（补充统计表情）
                result = {
                    "账号": user_name,
                    "统计": {
                        "总贴吧数": total,
                        "✅ 签到成功": success,
                        "ℹ️ 已签到": exist,
                        "🚫 被屏蔽": shield,
                        "❌ 签到失败": error
                    },
                    "状态": "🎉 签到完成"
                }
                
                msg = (
                    f"{user_name}\n"
                    f"📊 贴吧总数: {total}\n"
                    f"✅ 签到成功: {success}\n"
                    f"ℹ️ 已经签到: {exist}\n"
                    f"🚫 被屏蔽的: {shield}\n"
                    f"❌ 签到失败: {error}"
                )
                msg_all += msg + "\n\n"
                
                # 发送成功通知
                self.notifier.send(
                    title=f"百度贴吧签到通知 - {user_name}",
                    content=result
                )
                
            else:
                # 登录失败处理
                msg = f"{user_name}\n❌ 签到状态: {tbs}"  # tbs此处为错误信息
                msg_all += msg + "\n\n"
                self.notifier.send(
                    title=f"百度贴吧签到失败 - {user_name}",
                    content={"状态": "❌ 签到失败", "原因": tbs, "账号": user_name},
                    level="error"
                )
        
        return msg_all


def string_to_dict(s):
    """🔧 解析Cookie字符串为字典"""
    return {'cookie': s.split('#')[0]} if '#' in s else {'cookie': s}


def start():
    """🚀 程序入口"""
    # 初始化通知器
    notifier = Notifier(
        push_token=os.environ.get('PUSH_PLUS_TOKEN', ''),
        ql_url=os.environ.get('QL_API_URL', ''),
        ql_token=os.environ.get('QL_API_TOKEN', '')
    )
    
    # 获取环境变量配置
    tieback = os.getenv("tieback")
    if not tieback:
        print("⚠️  错误: 未配置tieback环境变量")
        notifier.send(
            title="百度贴吧签到配置错误",
            content={"状态": "❌ 配置错误", "原因": "未设置tieback环境变量"},
            level="error"
        )
        return
    
    # 解析多账号
    accounts = tieback.split('#') if '#' in tieback else [tieback]
    print(f"👥 检测到 {len(accounts)} 个账号，开始执行签到...")
    
    # 执行签到
    check_items = [string_to_dict(acc) for acc in accounts]
    tieba = Tieba(check_items, notifier)
    result = tieba.main()
    print("\n" + result)


if __name__ == "__main__":
    start()
