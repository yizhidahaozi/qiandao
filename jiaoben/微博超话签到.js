// 源码来自https://github.com/CCRSRG/weiboqiandao
// 修改时间2025年10月25日

// ==================== 配置区域 ====================
// 请在这里填写你的微博 Cookie
// 浏览器打开https://m.weibo.cn/p/tabbar?containerid=100803_-_recentvisit
// 按F12打开开发者工具，登录-点击network-找到tabbar?containerid=100803_-_recentvisit 查看里面的cookie

//    SUB: "你的SUB_cookie值",
//    SUBP: "你的SUBP值",
//    _T_WM: "你的_T_WM值",
    
// 微博超话自动签到（单/多账号兼容版）环境变量和内置2选1即可
// 支持：1. 脚本内直接填写Cookie（单账号）；2. 青龙环境变量多账号（WEIBO_COOKIE_1、WEIBO_COOKIE_2（格式同之前）） 脚本会优先读取环境变量，忽略 SINGLE_ACCOUNT_CONFIG 区的配置，自动执行多账号签到。
// 依赖：青龙需安装 NodeJs 下的 axios

// ==================== 单账号配置区（原始登录方式）====================
// 若使用多账号环境变量，此区域配置会被忽略
const SINGLE_ACCOUNT_CONFIG = {
    SUB: "", // 你的SUB Cookie（单账号必填）
    SUBP: "", // 你的SUBP Cookie（单账号必填）
    _T_WM: "", // 你的_T_WM Cookie（单账号必填）
    CHECKIN_DELAY: 1500, // 签到延迟（毫秒）
    VERBOSE: true        // 详细日志
};

// ==================== 全局配置 ====================
const GLOBAL_CONFIG = {
    ACCOUNT_DELAY: 3000, // 多账号间延迟（毫秒）
    PUSHPLUS: {
        enabled: true,
        token: "你的PushPlus_Token", // PushPlus令牌（无需通知可留空并将enabled设为false）
        url: "https://www.pushplus.plus/send/"
    }
};

// 请求头配置
const HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "MWeibo-Pwa": "1",
    "Referer": "https://m.weibo.cn/p/tabbar?containerid=100803_-_recentvisit&page_type=tabbar",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
};

// 引入依赖（青龙需提前安装axios）
const axios = require('axios');
axios.defaults.timeout = 10000; // 全局请求超时（10秒）
const allResults = []; // 存储所有账号结果

// ==================== 工具函数 ====================

/**
 * 日志输出（带账号标识）
 */
function log(message, type = 'info', accountId = '单账号') {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    const prefix = {
        'info': '[信息]',
        'success': '[成功]',
        'error': '[错误]',
        'warn': '[警告]'
    }[type] || '[信息]';
    console.log(`[${timestamp}] [${accountId}] ${prefix} ${message}`);
}

/**
 * 解析Cookie字符串为对象
 */
function parseCookie(cookieStr) {
    const cookieObj = {};
    if (!cookieStr) return cookieObj;
    cookieStr.split(';').forEach(item => {
        const [key, value] = item.trim().split('=');
        if (key && value) cookieObj[key] = value;
    });
    return cookieObj;
}

/**
 * 获取所有账号（优先环境变量多账号，其次脚本内单账号）
 */
function getAccounts() {
    // 1. 尝试读取环境变量多账号
    const envAccounts = [];
    let i = 1;
    while (true) {
        const envKey = `WEIBO_COOKIE_${i}`;
        const cookieStr = process.env[envKey];
        if (!cookieStr) break;
        const cookieObj = parseCookie(cookieStr);
        if (cookieObj.SUB && cookieObj.SUBP && cookieObj._T_WM) {
            envAccounts.push({ id: `账号${i}`, cookie: cookieObj });
            log(`已加载环境变量账号${i}`, 'info');
        } else {
            log(`环境变量账号${i}Cookie不完整，已跳过`, 'warn');
        }
        i++;
    }
    if (envAccounts.length > 0) return envAccounts;

    // 2. 若没有多账号，使用脚本内的单账号配置（原始登录方式）
    const singleCookie = {
        SUB: SINGLE_ACCOUNT_CONFIG.SUB,
        SUBP: SINGLE_ACCOUNT_CONFIG.SUBP,
        _T_WM: SINGLE_ACCOUNT_CONFIG._T_WM
    };
    if (singleCookie.SUB && singleCookie.SUBP && singleCookie._T_WM) {
        log('未检测到多账号环境变量，使用脚本内单账号配置', 'info');
        return [{ id: '单账号', cookie: singleCookie }];
    }

    // 3. 无有效账号
    log('未检测到任何有效账号，请配置Cookie', 'error');
    return [];
}

/**
 * 发送通知
 */
async function sendNotification(title, content) {
    if (!GLOBAL_CONFIG.PUSHPLUS.enabled) return;
    const token = GLOBAL_CONFIG.PUSHPLUS.token;
    if (!token || token === "你的PushPlus_Token") {
        log('PushPlus Token未配置，跳过通知', 'warn');
        return;
    }

    try {
        const res = await axios.post(GLOBAL_CONFIG.PUSHPLUS.url, {
            token, title, content, template: "html"
        }, { headers: { "Content-Type": "application/json" } });

        if (res.status === 200 && res.data?.code === 200) {
            log('✅ PushPlus通知发送成功', 'success');
        } else {
            log(`PushPlus通知失败: ${res.data?.msg || '未知错误'}`, 'warn');
        }
    } catch (err) {
        log(`发送通知出错: ${err.message}`, 'warn');
    }
}

/**
 * 延迟函数
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 构建Cookie字符串
 */
function buildCookieString(cookieObj) {
    return [
        `SUB=${cookieObj.SUB}`,
        `SUBP=${cookieObj.SUBP}`,
        `_T_WM=${cookieObj._T_WM}`
    ].join('; ');
}

/**
 * 验证Cookie有效性（保留原始验证逻辑）
 */
async function verifyCookie(cookieObj, accountId) {
    log('正在验证Cookie有效性...', 'info', accountId);
    try {
        const cookieStr = buildCookieString(cookieObj);
        const res = await axios.get('https://m.weibo.cn/api/config', {
            headers: { ...HEADERS, 'Cookie': cookieStr }
        });

        if (res.status === 200 && res.data?.data?.login) {
            log('Cookie验证成功，已登录', 'success', accountId);
            return true;
        } else {
            log('Cookie已过期或无效，请更新', 'error', accountId);
            return false;
        }
    } catch (err) {
        log(`验证Cookie出错: ${err.message}`, 'error', accountId);
        return false;
    }
}

/**
 * 获取超话列表（保留原始分页逻辑）
 */
async function getSupertopicList(cookieObj, accountId) {
    const cookieStr = buildCookieString(cookieObj);
    const headers = { ...HEADERS, 'Cookie': cookieStr };
    let allCards = [];
    let pageCount = 1;
    let sinceId = null;

    try {
        while (true) {
            log(`正在获取第${pageCount}页超话数据...`, 'info', accountId);
            let url = "https://m.weibo.cn/api/container/getIndex?containerid=100803_-_followsuper";
            if (sinceId) url += `&since_id=${sinceId}`;

            const res = await axios.get(url, { headers });
            if (res.status !== 200) {
                log(`获取第${pageCount}页失败，状态码: ${res.status}`, 'error', accountId);
                break;
            }

            const data = res.data;
            if (data.ok !== 1) {
                log(`第${pageCount}页获取失败: ${data.msg || '未知错误'}`, 'error', accountId);
                break;
            }

            if (data.data?.cards && data.data.cards.length > 0) {
                allCards = allCards.concat(data.data.cards);
                log(`第${pageCount}页获取成功，含${data.data.cards.length}个卡片`, 'info', accountId);
            } else {
                log(`第${pageCount}页无数据`, 'info', accountId);
                break;
            }

            sinceId = data.data?.cardlistInfo?.since_id;
            if (!sinceId) {
                log('已到达最后一页', 'info', accountId);
                break;
            }

            pageCount++;
            await sleep(500);
        }

        log(`共获取${pageCount}页数据，含${allCards.length}个卡片`, 'success', accountId);
        return allCards;
    } catch (err) {
        log(`获取超话列表失败: ${err.message}`, 'error', accountId);
        return null;
    }
}

/**
 * 执行单个超话签到（保留原始签到逻辑）
 */
async function performCheckin(topicName, scheme, cookieObj, accountId) {
    if (!scheme?.startsWith('/api/container/button')) return false;

    try {
        const cookieStr = buildCookieString(cookieObj);
        const url = `https://m.weibo.cn${scheme}`;
        const res = await axios.get(url, {
            headers: { ...HEADERS, 'Cookie': cookieStr }
        });

        if (res.status === 200 && res.data?.ok === 1) {
            const msg = res.data?.data?.msg || '';
            return msg.includes('成功') || msg.includes('签到') || true;
        } else {
            return false;
        }
    } catch (err) {
        if (SINGLE_ACCOUNT_CONFIG.VERBOSE) {
            log(`签到${topicName}出错: ${err.message}`, 'error', accountId);
        }
        return false;
    }
}

/**
 * 处理超话签到（保留原始统计逻辑）
 */
async function processSupertopics(cards, cookieObj, accountId) {
    log('\n========== 开始处理超话签到 ==========', 'info', accountId);
    const stats = {
        totalTopics: 0,
        checkedInBefore: 0,
        newlyCheckedIn: 0,
        failedCheckin: 0
    };

    for (const card of cards) {
        if (!card?.card_group) continue;
        for (const groupItem of card.card_group) {
            if (!groupItem?.title_sub || !groupItem?.buttons) continue;

            stats.totalTopics++;
            const topicName = groupItem.title_sub;
            const desc1 = groupItem.desc1 || '';
            let canCheckin = false;
            let checkinScheme = null;

            for (const button of groupItem.buttons) {
                if (!button?.name) continue;
                const btnName = button.name;
                if (btnName === '签到') {
                    canCheckin = true;
                    checkinScheme = button.scheme;
                    break;
                } else if (btnName.includes('已签') || btnName === '明日再来') {
                    stats.checkedInBefore++;
                    log(`✓ ${topicName} - 今日已签到 (${desc1})`, 'info', accountId);
                    break;
                }
            }

            if (canCheckin && checkinScheme) {
                const success = await performCheckin(topicName, checkinScheme, cookieObj, accountId);
                if (success) {
                    stats.newlyCheckedIn++;
                    log(`✓ ${topicName} - 签到成功 (${desc1})`, 'success', accountId);
                } else {
                    stats.failedCheckin++;
                    log(`✗ ${topicName} - 签到失败 (${desc1})`, 'error', accountId);
                }
                await sleep(SINGLE_ACCOUNT_CONFIG.CHECKIN_DELAY);
            }
        }
    }

    return stats;
}

/**
 * 单个账号签到流程
 */
async function runAccountCheckin(account) {
    const { id: accountId, cookie: cookieObj } = account;
    log('\n=======================================', 'info', accountId);
    log(`开始执行${accountId}的超话签到`, 'info', accountId);
    log('=======================================', 'info', accountId);

    try {
        // 验证Cookie（原始逻辑）
        const cookieValid = await verifyCookie(cookieObj, accountId);
        if (!cookieValid) {
            allResults.push({ accountId, success: false, error: 'Cookie无效' });
            return;
        }

        // 获取超话列表（原始逻辑）
        const cards = await getSupertopicList(cookieObj, accountId);
        if (!cards || cards.length === 0) {
            allResults.push({ accountId, success: false, error: '未获取到超话数据' });
            log('未获取到超话数据，签到终止', 'error', accountId);
            return;
        }

        // 执行签到（原始逻辑）
        const stats = await processSupertopics(cards, cookieObj, accountId);

        // 输出统计（原始格式）
        const completionRate = ((stats.checkedInBefore + stats.newlyCheckedIn) / Math.max(stats.totalTopics, 1) * 100).toFixed(1);
        log('\n========== 签到统计 ==========', 'info', accountId);
        log(`总共关注超话: ${stats.totalTopics} 个`, 'info', accountId);
        log(`之前已签到: ${stats.checkedInBefore} 个`, 'info', accountId);
        log(`本次新签到: ${stats.newlyCheckedIn} 个`, 'success', accountId);
        log(`签到失败: ${stats.failedCheckin} 个`, stats.failedCheckin > 0 ? 'warn' : 'info', accountId);
        log(`总完成率: ${completionRate}%`, 'info', accountId);
        log('===================================\n', 'info', accountId);

        allResults.push({ accountId, success: true, stats, completionRate });

    } catch (err) {
        const errMsg = `签到异常: ${err.message}`;
        log(errMsg, 'error', accountId);
        allResults.push({ accountId, success: false, error: errMsg });
    }
}

/**
 * 发送汇总通知
 */
async function sendSummary() {
    if (allResults.length === 0) return;

    // 单账号时单独通知，多账号时汇总通知
    const isSingleAccount = allResults.length === 1 && allResults[0].accountId === '单账号';
    let title, content;

    if (isSingleAccount) {
        const result = allResults[0];
        if (!result.success) {
            title = '微博超话签到失败 ❌';
            content = `<p style="color: red;">${result.error}</p>`;
        } else {
            const { stats, completionRate } = result;
            title = '微博超话签到完成 ✅';
            content = `
                <h2>📊 签到统计</h2>
                <ul>
                    <li>总超话：${stats.totalTopics} 个</li>
                    <li>已签到：${stats.checkedInBefore} 个</li>
                    <li>新签到：<span style="color: green;">${stats.newlyCheckedIn} 个</span></li>
                    <li>失败：<span style="color: ${stats.failedCheckin > 0 ? 'red' : 'gray'};">${stats.failedCheckin} 个</span></li>
                    <li>完成率：<span style="color: ${completionRate >= 90 ? 'green' : 'orange'};">${completionRate}%</span></li>
                </ul>
                <p style="color: gray;">时间：${new Date().toLocaleString()}</p>
            `;
        }
    } else {
        // 多账号汇总
        let allSuccess = true;
        content = '<h2>📊 多账号签到汇总</h2>';
        allResults.forEach(result => {
            if (!result.success) allSuccess = false;
            content += `<p><b>${result.accountId}：</b>`;
            if (!result.success) {
                content += `<span style="color: red;">❌ ${result.error}</span></p>`;
            } else {
                const { stats, completionRate } = result;
                content += `
                    <ul>
                        <li>总超话：${stats.totalTopics}</li>
                        <li>新签到：<span style="color: green;">${stats.newlyCheckedIn}</span></li>
                        <li>失败：<span style="color: ${stats.failedCheckin > 0 ? 'red' : 'gray'};">${stats.failedCheckin}</span></li>
                        <li>完成率：${completionRate}%</li>
                    </ul>
                </p>`;
            }
        });
        content += `<p style="color: gray;">时间：${new Date().toLocaleString()}</p>`;
        title = allSuccess ? '多账号签到全部成功 ✅' : '多账号签到部分失败 ⚠️';
    }

    await sendNotification(title, content);
}

// ==================== 主函数 ====================
async function main() {
    log('========== 微博超话自动签到（兼容版） ==========\n', 'info');

    // 获取账号（优先多账号，其次单账号）
    const accounts = getAccounts();
    if (accounts.length === 0) return;

    // 依次执行签到
    for (const account of accounts) {
        await runAccountCheckin(account);
        // 多账号间延迟（最后一个账号无需延迟）
        if (accounts.length > 1 && account !== accounts[accounts.length - 1]) {
            log(`等待${GLOBAL_CONFIG.ACCOUNT_DELAY/1000}秒后执行下一个账号...\n`, 'info');
            await sleep(GLOBAL_CONFIG.ACCOUNT_DELAY);
        }
    }

    // 发送通知
    await sendSummary();
    log('\n========== 所有签到流程已完成 ==========', 'info');
}

// 执行入口
main();
