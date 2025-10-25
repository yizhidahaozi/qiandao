# 来自吾爱论坛，在原作者的基础上把推送消息换成了青龙自带的通知，修复了脚本在青龙容器运行不会自动停止的bug，如有侵权请告知，将立即删除。
# 修改时间 2025年10月25日
# @author Sten
# 转自仓库:https://github.com/aefa6/QinglongScript.git
# 感谢LeXrLt的提醒，无法运行的 https://e.dlife.cn/user/index.do ，打开上述网址登录后关闭设备锁即可继续使用签到脚本。
# 觉得不错关注原作者
# 关闭二次验证可完美运行登录签到  已删除报错抽奖功能
# 关闭二次验证地址 https://e.dlife.cn/portal/web/index.html#/login 
import notify
import time
import re
import json
import base64
import hashlib
import urllib.parse
import hmac
import rsa
import requests
import random
import os  # 用于读取环境变量
 
BI_RM = list("0123456789abcdefghijklmnopqrstuvwxyz")
B64MAP = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


# -------------------------下面账号密码填写二选一（可选） --------------------------

# -------------------------- 原始账号密码填写（可选） --------------------------
# 若未配置青龙环境变量，将使用此处的账号密码
username = ""  # 天翼云手机号
password = ""    # 天翼云密码
# --------------------------------------------------------------------------
 
# -------------------------- 优先读取青龙环境变量 --------------------------
# 变量名：TIANYIYUN_USER（天翼云手机号）、TIANYIYUN_PWD（天翼云密码）
env_user = os.getenv("TIANYIYUN_USER")
env_pwd = os.getenv("TIANYIYUN_PWD")
# 若环境变量存在，则覆盖原始账号密码
if env_user and env_pwd:
    username = env_user
    password = env_pwd
# --------------------------------------------------------------------------
 


# 🔑 校验账号密码是否存在（无论哪种方式）
assert username and password, "🔑 请填写账号密码（或在青龙配置环境变量TIANYIYUN_USER/TIANYIYUN_PWD）"
 
 
def int2char(a):
    return BI_RM[a]
 
 
def b64tohex(a):
    d = ""
    e = 0
    c = 0
    for i in range(len(a)):
        if list(a)[i] != "=":
            v = B64MAP.index(list(a)[i])
            if 0 == e:
                e = 1
                d += int2char(v >> 2)
                c = 3 & v
            elif 1 == e:
                e = 2
                d += int2char(c << 2 | v >> 4)
                c = 15 & v
            elif 2 == e:
                e = 3
                d += int2char(c)
                d += int2char(v >> 2)
                c = 3 & v
            else:
                e = 0
                d += int2char(c << 2 | v >> 4)
                d += int2char(15 & v)
    if e == 1:
        d += int2char(c << 2)
    return d
 
 
def rsa_encode(j_rsakey, string):
    rsa_key = f"-----BEGIN PUBLIC KEY-----\n{j_rsakey}\n-----END PUBLIC KEY-----"
    pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(rsa_key.encode())
    result = b64tohex((base64.b64encode(rsa.encrypt(f'{string}'.encode(), pubkey))).decode())
    return result
 
 
def login(username, password):
    """登录函数：返回会话对象（失败时返回None）"""
    s = requests.Session()
    # 获取登录令牌
    url_token = "https://m.cloud.189.cn/udb/udb_login.jsp?pageId=1&pageKey=default&clientType=wap&redirectURL=https://m.cloud.189.cn/zhuanti/2021/shakeLottery/index.html"
    try:
        print("🔄 正在获取登录令牌...")
        r = s.get(url_token, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 获取登录令牌失败：{str(e)}")
        notify.send("❌ 天翼云签到失败", f"⚠️ 获取登录令牌失败：{str(e)}")
        return None
 
    # 提取跳转URL
    pattern_url = r"https?://[^\s'\"]+"
    match_url = re.search(pattern_url, r.text)
    if not match_url:
        print(f"🔍 未找到登录跳转URL")
        notify.send("❌ 天翼云签到失败", f"🔍 未找到登录跳转URL")
        return None
    jump_url = match_url.group()
 
    # 提取账号密码登录入口
    try:
        print(f"🔄 正在访问跳转URL...")
        r = s.get(jump_url, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 访问跳转URL失败：{str(e)}")
        notify.send("❌ 天翼云签到失败", f"⚠️ 访问跳转URL失败：{str(e)}")
        return None
 
    pattern_href = r"<a id=\"j-tab-login-link\"[^>]*href=\"([^\"]+)\""
    match_href = re.search(pattern_href, r.text)
    if not match_href:
        print(f"🚪 未找到账号密码登录入口")
        notify.send("❌ 天翼云签到失败", f"🚪 未找到账号密码登录入口")
        return None
    login_href = match_href.group(1)
 
    # 提取登录参数
    try:
        print(f"🔄 正在获取登录参数...")
        r = s.get(login_href, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 获取登录参数失败：{str(e)}")
        notify.send("❌ 天翼云签到失败", f"⚠️ 获取登录参数失败：{str(e)}")
        return None
 
    try:
        captcha_token = re.findall(r"captchaToken' value='(.+?)'", r.text)[0]
        lt = re.findall(r'lt = "(.+?)"', r.text)[0]
        return_url = re.findall(r"returnUrl= '(.+?)'", r.text)[0]
        param_id = re.findall(r'paramId = "(.+?)"', r.text)[0]
        j_rsakey = re.findall(r'j_rsaKey" value="(\S+)"', r.text, re.M)[0]
    except IndexError:
        print(f"🔄 提取登录参数失败（页面结构可能变化）")
        notify.send("❌ 天翼云签到失败", f"🔄 提取登录参数失败（页面结构可能变化）")
        return None
 
    s.headers.update({"lt": lt})
    print("🔄 正在加密账号密码...")
    # RSA加密账号密码
    encrypted_username = rsa_encode(j_rsakey, username)
    encrypted_password = rsa_encode(j_rsakey, password)
 
    # 提交登录请求
    login_url = "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/76.0',
        'Referer': 'https://open.e.189.cn/',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        "appKey": "cloud",
        "accountType": '01',
        "userName": f"{{RSA}}{encrypted_username}",
        "password": f"{{RSA}}{encrypted_password}",
        "validateCode": "",
        "captchaToken": captcha_token,
        "returnUrl": return_url,
        "mailSuffix": "@189.cn",
        "paramId": param_id
    }
 
    try:
        print("🔄 正在提交登录请求...")
        r = s.post(login_url, data=data, headers=headers, timeout=10)
        r.raise_for_status()
        response_data = r.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 发送登录请求失败：{str(e)}")
        notify.send("❌ 天翼云签到失败", f"⚠️ 发送登录请求失败：{str(e)}")
        return None
    except json.JSONDecodeError:
        print(f"🔄 登录响应不是合法JSON（可能页面跳转）")
        notify.send("❌ 天翼云签到失败", f"🔄 登录响应不是合法JSON（可能页面跳转）")
        return None
 
    # 处理登录结果
    if response_data.get('result') == 0:
        print("✅ 账号登录成功")
    else:
        error_msg = response_data.get('msg', '未知登录错误')
        print(f"❌ 登录失败：{error_msg}")
        notify.send("❌ 天翼云签到失败", f"❌ 登录失败：{error_msg}\n🔒 建议：访问https://e.dlife.cn/user/index.do关闭设备锁")
        return None
 
    # 获取跳转链接
    redirect_url = response_data.get('toUrl')
    if not redirect_url:
        print(f"🔒 登录成功但未获取到跳转链接（可能需二次验证）")
        notify.send("❌ 天翼云签到失败", f"🔒 登录成功但未获取到跳转链接（需关闭设备锁）")
        return None
 
    # 跳转至签到页面
    try:
        print("🔄 正在跳转至签到页面...")
        r = s.get(redirect_url, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 跳转至签到页面失败：{str(e)}")
        notify.send("❌ 天翼云签到失败", f"⚠️ 跳转至签到页面失败：{str(e)}")
        return None
 
    return s
 
 
def get_account_basic_info():
    """仅返回账号名（表情在前）"""
    return {
        "username": f"👤 账号：{username}"
    }
 
 
def main():
    """主函数：兼容环境变量和原始账号密码，保持排序和表情"""
    # 1. 登录
    s = login(username, password)
    if not s:
        print("🛑 登录流程终止，无法继续操作")
        return
 
    # 2. 基础签到
    rand = str(round(time.time() * 1000))
    sign_url = f'https://api.cloud.189.cn/mkt/userSign.action?rand={rand}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
        "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
        "Host": "m.cloud.189.cn",
        "Accept-Encoding": "gzip, deflate",
    }
    sign_result = "❌ 基础签到：未知错误"
    try:
        print("🔄 正在执行基础签到...")
        response = s.get(sign_url, headers=headers, timeout=10)
        response.raise_for_status()
        sign_data = response.json()
        netdisk_bonus = sign_data.get('netdiskBonus', '未知')
        if sign_data.get('isSign') == "false":
            sign_result = f"🎁 基础签到：未签到，获得{netdisk_bonus}M空间"
        else:
            sign_result = f"✅ 基础签到：已签到，获得{netdisk_bonus}M空间"
        print(sign_result)
    except Exception as e:
        sign_result = f"❌ 基础签到失败：{str(e)}"
        print(sign_result)
 
    # 3. 账号信息（精简格式）
    account_info = get_account_basic_info()
    info_result = f"📊 账号信息\n{account_info['username']}"
 
    # 4. 推送结果（账号信息在前，签到结果在后）
    title = "📱 天翼云盘签到完成"
    content = f"{info_result}\n{sign_result}"
    print(f"\n{title}\n{content}")
    notify.send(title, content)
 
    # 5. 延迟退出
    exit_delay = random.randint(5, 30)
    print(f"⏳ 脚本即将在{exit_delay}秒后退出...")
    time.sleep(exit_delay)
 
 
# 平台入口函数
def lambda_handler(event, context):
    main()
 
def main_handler(event, context):
    main()
 
def handler(event, context):
    main()
 
if __name__ == "__main__":
    main()
