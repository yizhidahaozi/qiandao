#!/usr/bin/python3
# -- coding: utf-8 --
# -------------------------------
# @Author : 优化版富贵论坛签到脚本
# @Time : 2025/7/1
# -------------------------------
# cron "1 0 * * *" script-path=xxx.py,tag=匹配cron用
# const $ = new Env('富贵论坛签到');

import requests
import re
import time
import json
import os
import notify
import random
import hashlib
from datetime import datetime

class FGLTForumSignIn:
    def __init__(self, cookies):
        self.cookies = cookies
        self.base_url = 'https://www.fglt.net/'
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        self.signin_count_file = 'signin_count.json'
        self.load_signin_count()
    
    def load_signin_count(self):
        """加载签到统计信息"""
        try:
            if os.path.exists(self.signin_count_file):
                with open(self.signin_count_file, 'r') as f:
                    data = json.load(f)
                    self.signin_count = data.get('count', 0)
                    self.last_signin_date = data.get('last_date', '')
            else:
                self.signin_count = 0
                self.last_signin_date = ''
        except Exception as e:
            print(f"加载签到统计失败: {e}")
            self.signin_count = 0
            self.last_signin_date = ''
    
    def save_signin_count(self):
        """保存签到统计信息"""
        try:
            data = {
                'count': self.signin_count,
                'last_date': self.last_signin_date,
            }
            with open(self.signin_count_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"保存签到统计失败: {e}")
    
    def check_need_signin(self):
        """检查今天是否需要签到"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.last_signin_date != today
    
    def get_formhash(self, session):
        """获取签到所需的formhash参数"""
        time.sleep(random.uniform(2, 5))
        
        try:
            pages = [
                self.base_url,
                f"{self.base_url}forum.php",
                f"{self.base_url}home.php",
                f"{self.base_url}plugin.php?id=dsu_amupper",
                f"{self.base_url}home.php?mod=spacecp"
            ]
            
            for page in pages:
                print(f"尝试从 {page} 获取formhash")
                time.sleep(random.uniform(1, 3))
                
                response = session.get(page)
                response.raise_for_status()
                
                verification_keywords = [
                    "安全验证", "验证码", "verification", "captcha", "security", "需要登录", "请登录"
                ]
                if any(keyword in response.text for keyword in verification_keywords):
                    print("检测到安全验证页面，无法继续签到")
                    print(f"页面内容片段: {response.text[:200]}")
                    return None
                
                patterns = [
                    r'<input type="hidden" name="formhash" value="(.*?)" />',
                    r'formhash=(.*?)[&\'" ]',
                    r'"formhash":"(.*?)"',
                    r'formhash=(\w+)',
                    r'<input type="hidden" id="formhash" value="(.*?)"',
                    r'var formhash = "(.*?)"'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        print(f"成功从 {page} 获取到formhash，使用模式: {pattern}")
                        return match.group(1)
            
            print("未能在任何页面中获取到formhash")
            print(f"页面内容片段: {response.text[:300]}")
            return None
        except requests.RequestException as e:
            print(f"获取formhash请求失败: {e}")
            return None
    
    def sign_in(self, cookie):
        """执行单个账号的签到操作"""
        session = requests.Session()
        session.headers.update(self.get_random_headers())
        session.cookies.update(self.parse_cookie(cookie))
        
        # 检查是否需要签到
        today = datetime.now().strftime('%Y-%m-%d')
        need_signin = self.check_need_signin()
        
        # 获取formhash
        formhash = self.get_formhash(session)
        if not formhash:
            return "获取formhash失败，签到终止"
        
        print(f'获取到formhash: {formhash}')
        
        # 执行签到
        sign_url = f"{self.base_url}plugin.php?id=dsu_amupper&ppersubmit=true&formhash={formhash}&infloat=yes&handlekey=dsu_amupper&inajax=1&ajaxtarget=fwin_content_dsu_amupper"
        
        try:
            response = session.post(sign_url)
            response.raise_for_status()
            
            # 解析签到结果
            result = None
            
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                cdata_content = root.text
                if cdata_content:
                    patterns = [
                        r'showDialog\("(.*?)",',
                        r'"message":"(.*?)"',
                        r'<div class="alert_info">(.*?)</div>',
                        r'<div class="alert_success">(.*?)</div>',
                        r'签到成功',
                        r'已签到',
                        r'您今日已经签到',
                        r'恭喜你签到成功',
                        r'签到排名第(.*?)名'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, cdata_content)
                        if match:
                            result = match.group(1) if len(match.groups()) > 0 else pattern
                            break
            except:
                pass
            
            if not result:
                patterns = [
                    r'showDialog\("(.*?)",',
                    r'"message":"(.*?)"',
                    r'<div class="alert_info">(.*?)</div>',
                    r'<div class="alert_success">(.*?)</div>',
                    r'签到成功',
                    r'已签到',
                    r'您今日已经签到',
                    r'恭喜你签到成功',
                    r'签到排名第(.*?)名'
                ]
                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        result = match.group(1) if len(match.groups()) > 0 else pattern
                        break
            
            if result:
                if "成功" in result or "已签到" in result:
                    if need_signin and self.check_need_signin():
                        self.signin_count += 1
                        self.last_signin_date = today
                        self.save_signin_count()
                        return f"签到成功，今日第{self.signin_count}次签到"
                    else:
                        return f"{result}，今日已签到{self.signin_count}次"
                else:
                    return result
            else:
                return f"签到成功，今日第{self.signin_count}次签到"
        except requests.RequestException as e:
            return f"签到请求失败: {e}"
    
    def get_random_headers(self):
        """获取随机请求头，增强反爬能力"""
        headers = self.headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        return headers
    
    def parse_cookie(self, cookie_str):
        """将cookie字符串解析为字典格式"""
        try:
            return dict(item.split('=', 1) for item in cookie_str.split('; ') if '=' in item)
        except ValueError:
            print(f"解析cookie失败: {cookie_str}")
            return {}
    
    def run(self):
        """执行所有账号的签到操作"""
        success_results = []
        failed_results = []
        
        for i, cookie in enumerate(self.cookies, 1):
            print(f"\n***开始第{i}个账号签到***")
            cookie_hash = hashlib.md5(cookie.encode('utf-8')).hexdigest()[:8]
            print(f"处理账号 (哈希): {cookie_hash}")
            
            result = self.sign_in(cookie)
            print(result)
            
            if "签到成功" in result or "已签到" in result:
                success_results.append(f"账号{i}: {result}")
            else:
                failed_results.append(f"账号{i}: {result}")
            
            delay = random.uniform(8, 15)
            print(f"等待{delay:.2f}秒后处理下一个账号")
            time.sleep(delay)
        
        # 只发送成功的签到提醒
        if success_results:
            success_summary = "\n\n".join(success_results)
            notify.send("富贵论坛签到成功提醒", success_summary)
            print("\n成功通知内容:")
            print(success_summary)
        
        # 打印失败的结果，但不发送通知
        if failed_results:
            print("\n失败的签到结果:")
            print("\n\n".join(failed_results))
        
        return success_results, failed_results

if __name__ == "__main__":
    fg_cookies = os.getenv("fg_cookies", "").split('&')
    
    if not fg_cookies or fg_cookies[0] == "":
        print("未配置cookie，退出程序")
    else:
        print(f"共配置了{len(fg_cookies)}个账号")
        
        start_delay = random.uniform(15, 45)
        print(f"随机延迟{start_delay:.2f}秒后开始")
        time.sleep(start_delay)
        
        sign_bot = FGLTForumSignIn(fg_cookies)
        success, failed = sign_bot.run()
        
        if not failed:
            print("所有账号签到成功")
        else:
            print(f"{len(failed)}/{len(fg_cookies)}个账号签到失败")
