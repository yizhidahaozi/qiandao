# name: 葫芦侠三楼
# Author: sicxs
# Date: 2024-12-16
# export app_hlx="手机号#密码"
# 换行 & 分割 
# 功能:签到
# cron: 18 8 * * *
# new Env('葫芦侠三楼');
from notify import send

import json
import hashlib
import requests,random
import time,re,os,sys
def pr(message):
    msg.append(message +  "\n")
    print(message)

msg = []
def index(username,password): #登录信息
    password = hashlib.md5(password.encode('utf-8')).hexdigest()
    sign = "account" + username + "device_code[d]b305cc73-8db8-4a25-886f-e73c502b1e99password" + password + "voice_codefa1c28a5b62e79c3e63d9030b6142e4b"
    sign = hashlib.md5(sign.encode('utf-8')).hexdigest()
    url = "http://floor.huluxia.com/account/login/ANDROID/4.1.8?platform=2&gkey=000000&app_version=4.3.0.7.1&versioncode=367&market_id=tool_web&_key=&device_code=%5Bd%5Db305cc73-8db8-4a25-886f-e73c502b1e99&phone_brand_type=VO"
    data = {
    'account': username,
    'login_type': '2',
    'password': password,
    'sign': sign}
    headers = {"User-Agent": "okhttp/3.8.1"}
    response = requests.post(url=url, data=data, headers=headers)
    response.encoding = "utf-8"
    info = json.loads(response.text)    
    key = info['_key']
    pr(f"登陆成功，用户名：{info['user']['nick']}")
    app_qiandao(key)
    
def app_qiandao(key): #签到
    pr("开始执行签到任务...")
    id = app_list()
    for i in id:
      timestamp = int(time.time() * 1000)
      sign = "cat_id" + str(i[0]) + "time" + str(timestamp) + "fa1c28a5b62e79c3e63d9030b6142e4b"
      sign = hashlib.md5(sign.encode('utf-8')).hexdigest()
      url = f"http://floor.huluxia.com/user/signin/ANDROID/4.1.8?platform=2&gkey=000000&app_version=4.3.0.7.1&versioncode=20141475&market_id=floor_web&_key={key}&phone_brand_type=OP&cat_id={i[0]}&time={timestamp}"
      headers = {
                "Accept-Encoding": "identity",
                "Host": "floor.huluxia.com",
                'User-Agent': 'okhttp/3.8.1',
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": "37"
            }
      data =  { "sign": sign }
      time.sleep(random.randint(15,20))
      response = requests.post(url=url, headers=headers,data=data)
      response.encoding = "utf-8"
      info = json.loads(response.text)  
      if 1 == info['status']:
          pr(f"{i[1]} 签到成功，获得{info['experienceVal']}点经验")
      else:
         pr(f"{i[1]},{info['msg']}")
    pr("签到完成")
def app_list(): #板块列表
    list = []
    url = f"https://floor.huluxia.com/category/list/ANDROID/4.2.3?"
    headers = {
        "Host": "floor.huluxia.com",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": "\"Microsoft Edge\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        }
    response = requests.get(url=url, headers=headers)
    response.encoding = "utf-8"
    info = json.loads(response.text)
    if info['status'] == 1:
      for i in info['categories']:
        id = i['categoryID']
        title = i['title']
        list.append((id,title))
    else:
      pr("获取失败")
    return list  

def sicxs():
    config_path = 'config.py'
    if os.path.exists(config_path):
      import config  
    else:
      with open(config_path, 'w') as f: 
        pr("首次运行，已创建配置文件 config.py，请按照说明填写相关变量后再次运行脚本。")
        f.write('#可以在此文件中添加配置变量，例如：\nsfsy = ""\n')
    try:
        env_cookie = os.environ.get("app_hlx")
        si_cookie = getattr(config, 'app_hlx', '') 
        if env_cookie and si_cookie:
            cookies = env_cookie + "\n" + si_cookie
        elif env_cookie:
            cookies = env_cookie
        elif si_cookie:
            cookies = si_cookie
        else:
            pr("请设置变量 export app_hlx='' 或在 config.py 中设置 app_hlx =")
            sys.exit()
    except Exception as e:
        pr("请设置变量 export app_hlx='' 或在 config.py 中设置 app_hlx =")
        sys.exit()

    list_cookie = re.split(r'\n|&', cookies)
    total_cookies = len(list_cookie)
    
    for i, list_cookie_i in enumerate(list_cookie):
        try:
            print(f'\n----------- 账号【{i + 1}/{total_cookies}】执行 -----------')
            pr(f"账号【{i + 1}】开始执行：")
            list = list_cookie_i.split("#")
            index(list[0], list[1])
        except Exception as e:
            print(f"账号【{i + 1}/{total_cookies}】执行出错")    
        finally:
            send("葫芦侠三楼", ''.join(msg))
            msg.clear()
    pr(f'\n-----------  执 行  结 束 -----------')

if __name__ == '__main__':
   sicxs()
