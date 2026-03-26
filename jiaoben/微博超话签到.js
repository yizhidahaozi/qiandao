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

// 核心特点：1. 账号名=主脚本规则（单账号/账号1/账号2）；2. 通知全用辅脚本逻辑（含表情、青龙适配、格式）
// 依赖：axios（青龙：node-axios；本地：npm install axios）

// ==================== 基础配置 ====================
// 单账号配置（多账号环境变量存在时忽略）
const SINGLE_ACCOUNT_CONFIG = {
    SUB: "", // 单账号SUB Cookie
    SUBP: "", // 单账号SUBP Cookie
    _T_WM: "", // 单账号_T_WM Cookie
    CHECKIN_DELAY: 1500, // 超话间签到延迟（毫秒）
    VERBOSE: true // 详细日志
};

// 全局配置（通知用辅脚本规则）
const GLOBAL_CONFIG = {
    ACCOUNT_DELAY: 3000, // 多账号间延迟（毫秒）
    NOTIFY: {
        enabled: true,      // 开启通知
        forceSend: true     // 强制发送（即使无结果）
    }
};


"""
cron: 35 9 * * *
new Env('微博超话签到');
"""


// ==================== 依赖与请求配置 ====================
const axios = require('axios');
const fs = require('fs');
axios.defaults.timeout = 15000;

// 请求头（模拟浏览器）
const HEADERS = {
    "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Host": "m.weibo.cn",
    "Referer": "https://m.weibo.cn/p/tabbar?containerid=100803_-_recentvisit",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
};

// 全局结果存储
const allResults = [];
const signResults = []; // 通知汇总（带辅脚本表情）

// ==================== 通知模块（全用辅脚本逻辑，含表情） ====================
let notify = { send: async () => {} }; // 通知实例

/**
 * 检查文件存在性（辅脚本逻辑）
 */
function checkFileExists(path) {
    try {
        return fs.existsSync(path);
    } catch (err) {
        console.log(`⚠️ 检查文件失败：${err.message}`);
        return false;
    }
}

/**
 * 初始化通知（辅脚本核心逻辑：优先青龙notify.js，次选PUSH_PLUS_TOKEN）
 */
async function initNotify() {
    try {
        // 1. 加载青龙notify.js（多路径适配）
        const qlPaths = ['/ql/scripts/notify.js', '/ql/notify.js', '/root/notify.js'];
        const qlNotifyPath = qlPaths.find(path => checkFileExists(path));
        if (qlNotifyPath) {
            delete require.cache[require.resolve(qlNotifyPath)];
            notify = require(qlNotifyPath);
            if (typeof notify.send === 'function') {
                console.log(`📌 加载青龙通知脚本：${qlNotifyPath}`);
                return;
            }
        }

        // 2. 用青龙环境变量PUSH_PLUS_TOKEN
        if (process.env.PUSH_PLUS_TOKEN) {
            const token = process.env.PUSH_PLUS_TOKEN.trim();
            notify.send = async (title, content) => {
                await axios.post('https://www.pushplus.plus/send', {
                    token, title, content, template: "txt"
                }, { headers: { 'Content-Type': 'application/json' } });
            };
            console.log(`📌 启用Push Plus通知（已读Token）`);
            return;
        }

        // 3. 降级为日志通知（带表情）
        notify.send = async (title, content) => {
            console.log(`\n[通知] ${title}\n${content}\n`);
        };
        console.log(`📌 启用日志通知（无青龙notify/Token）`);
    } catch (err) {
        notify.send = async (title, content) => {
            console.log(`\n[通知] ${title}\n${content}\n`);
        };
        console.log(`⚠️ 通知初始化失败：${err.message}`);
    }
}
initNotify();

/**
 * 发送通知（辅脚本格式：带表情标题）
 */
async function sendNotify(title, content) {
    if (!GLOBAL_CONFIG.NOTIFY.enabled) return;
    const finalTitle = `微博超话签到 - ${title}`; // 标题保留辅脚本简洁风格
    const finalContent = content || "无结果";
    try {
        await notify.send(finalTitle, finalContent);
        console.log(`📤 通知发送成功`);
    } catch (err) {
        console.log(`❌ 通知发送失败：${err.message}`);
        console.log(`[标题] ${finalTitle}\n[内容] ${finalContent}`);
    }
}

/**
 * 发送汇总通知（辅脚本逻辑：带表情汇总结果）
 */
async function sendSummary() {
    // 强制发送空结果（带警告表情）
    if (signResults.length === 0 && GLOBAL_CONFIG.NOTIFY.forceSend) {
        signResults.push("⚠️ 未处理任何有效账号");
    }
    // 用表情区分整体状态
    const hasError = signResults.some(item => item.startsWith('❌') || item.startsWith('⚠️'));
    const title = hasError ? "部分失败 ⚠️" : "全部成功 ✅";
    await sendNotify(title, signResults.join('\n\n'));
}

// ==================== 工具函数（日志带辅脚本表情） ====================
/**
 * 日志输出（辅脚本风格：带表情+账号名）
 */
function log(message, type = 'info', accountId = '单账号') {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    const [prefix, emoji] = {
        'info': ['[信息]', 'ℹ️'],   // 信息用ℹ️
        'success': ['[成功]', '✅'], // 成功用✅
        'error': ['[错误]', '❌'],   // 错误用❌
        'warn': ['[警告]', '⚠️']    // 警告用⚠️
    }[type] || ['[信息]', 'ℹ️'];
    console.log(`[${timestamp}] ${emoji} [${accountId}] ${prefix} ${message}`);
}

/**
 * 延迟函数
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 解析Cookie字符串
 */
function parseCookie(cookieStr) {
    const cookieObj = {};
    if (!cookieStr) return cookieObj;
    cookieStr.split(';').forEach(item => {
        const [key, ...valueParts] = item.trim().split('=');
        const value = valueParts.join('=');
        if (key && value) cookieObj[key] = value;
    });
    return cookieObj;
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

// ==================== 账号处理（主脚本规则：单账号/账号1/账号2） ====================
/**
 * 获取账号（主脚本逻辑）
 */
function getAccounts() {
    // 1. 多账号：WEIBO_COOKIE_1→账号1，WEIBO_COOKIE_2→账号2...
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

    // 2. 单账号：脚本内配置→账号名=“单账号”
    const singleCookie = {
        SUB: SINGLE_ACCOUNT_CONFIG.SUB,
        SUBP: SINGLE_ACCOUNT_CONFIG.SUBP,
        _T_WM: SINGLE_ACCOUNT_CONFIG._T_WM
    };
    if (singleCookie.SUB && singleCookie.SUBP && singleCookie._T_WM) {
        log('未检测到多账号，使用单账号配置', 'info');
        return [{ id: '单账号', cookie: singleCookie }];
    }

    // 3. 无有效账号（带警告表情）
    log('未检测到任何有效账号，请配置Cookie', 'error');
    return [];
}

// ==================== 超话处理与签到（保留核心逻辑，日志带表情） ====================
/**
 * 验证Cookie有效性
 */
async function verifyCookie(cookieObj, accountId) {
    log('验证Cookie有效性...', 'info', accountId);
    try {
        const cookieStr = buildCookieString(cookieObj);
        const res = await axios.get('https://m.weibo.cn/api/config', {
            headers: { ...HEADERS, 'Cookie': cookieStr }
        });

        if (res.status === 200 && res.data?.data?.login) {
            log('Cookie验证成功，已登录', 'success', accountId); // 成功带✅
            return true;
        } else {
            log('Cookie无效（未登录/已过期）', 'error', accountId); // 失败带❌
            return false;
        }
    } catch (err) {
        log(`Cookie验证失败：${err.message}`, 'error', accountId); // 失败带❌
        return false;
    }
}

/**
 * 获取超话列表（带分页重试）
 */
async function getSupertopicList(cookieObj, accountId) {
    const cookieStr = buildCookieString(cookieObj);
    const headers = { ...HEADERS, 'Cookie': cookieStr };
    let allCards = [];
    let pageCount = 1;
    let sinceId = null;
    const maxRetries = 2;

    try {
        while (true) {
            let res;
            // 带重试请求
            for (let retry = 0; retry <= maxRetries; retry++) {
                try {
                    log(`获取第${pageCount}页超话（重试${retry}/${maxRetries}）`, 'info', accountId);
                    let url = "https://m.weibo.cn/api/container/getIndex?containerid=100803_-_followsuper";
                    if (sinceId) url += `&since_id=${sinceId}`;

                    res = await axios.get(url, { headers });
                    break;
                } catch (err) {
                    if (retry === maxRetries) throw err;
                    await sleep(1000 * (retry + 1));
                    log(`第${pageCount}页请求失败，${retry + 1}秒后重试`, 'warn', accountId); // 警告带⚠️
                }
            }

            if (res.status !== 200) {
                log(`第${pageCount}页获取失败（状态码：${res.status}）`, 'error', accountId); // 失败带❌
                break;
            }

            const data = res.data;
            if (data.ok !== 1) {
                log(`第${pageCount}页获取失败：${data.msg || '未知错误'}`, 'error', accountId); // 失败带❌
                break;
            }

            const currentCards = data.data?.cards || [];
            if (currentCards.length > 0) {
                allCards = allCards.concat(currentCards);
                log(`第${pageCount}页解析完成，新增${currentCards.length}个超话`, 'info', accountId); // 信息带ℹ️
            } else {
                log(`第${pageCount}页无数据`, 'info', accountId); // 信息带ℹ️
                break;
            }

            sinceId = data.data?.cardlistInfo?.since_id;
            if (!sinceId) {
                log(`已获取所有超话（共${allCards.length}个）`, 'success', accountId); // 成功带✅
                break;
            }

            pageCount++;
            await sleep(500);
        }

        return allCards;
    } catch (err) {
        log(`超话列表获取异常：${err.message}`, 'error', accountId); // 失败带❌
        return null;
    }
}

/**
 * 单个超话签到
 */
async function performCheckin(topicName, scheme, cookieObj, accountId) {
    if (!scheme?.startsWith('/api/container/button')) return false;

    try {
        const cookieStr = buildCookieString(cookieObj);
        const url = `https://m.weibo.cn${scheme}`;
        const res = await axios.get(url, { headers: { ...HEADERS, 'Cookie': cookieStr } });

        if (res.status === 200 && res.data?.ok === 1) {
            const msg = res.data?.data?.msg || '';
            return msg.includes('成功') || msg.includes('签到') || true;
        } else {
            return false;
        }
    } catch (err) {
        if (SINGLE_ACCOUNT_CONFIG.VERBOSE) {
            log(`签到${topicName}出错：${err.message}`, 'error', accountId); // 失败带❌
        }
        return false;
    }
}

/**
 * 批量处理超话签到（日志带辅脚本表情）
 */
async function processSupertopics(cards, cookieObj, accountId) {
    log('\n========== 开始超话签到 ==========', 'info', accountId);
    const stats = {
        totalTopics: 0,        // 总超话数
        checkedInBefore: 0,    // 已签到
        newlyCheckedIn: 0,     // 新签到成功
        failedCheckin: 0       // 签到失败
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
                    log(`【${topicName}】已签到（${desc1}）`, 'info', accountId); // 信息带ℹ️
                    break;
                }
            }

            if (canCheckin && checkinScheme) {
                const success = await performCheckin(topicName, checkinScheme, cookieObj, accountId);
                if (success) {
                    stats.newlyCheckedIn++;
                    log(`【${topicName}】签到成功（${desc1}）`, 'success', accountId); // 成功带✅
                } else {
                    stats.failedCheckin++;
                    log(`【${topicName}】签到失败：请重试（${desc1}）`, 'error', accountId); // 失败带❌
                }
                await sleep(SINGLE_ACCOUNT_CONFIG.CHECKIN_DELAY);
            }
        }
    }

    return stats;
}

// ==================== 主流程（结果汇总带辅脚本表情） ====================
async function runAccountCheckin(account) {
    const { id: accountId, cookie: cookieObj } = account;
    log('\n=======================================', 'info', accountId);
    log(`开始【${accountId}】超话签到流程`, 'info', accountId);
    log('=======================================', 'info', accountId);

    try {
        // 1. 验证Cookie
        const cookieValid = await verifyCookie(cookieObj, accountId);
        if (!cookieValid) {
            allResults.push({ accountId, success: false, error: 'Cookie无效' });
            signResults.push(`❌ ${accountId}：Cookie无效（请更新）`); // 带❌
            return;
        }

        // 2. 获取超话列表
        const cards = await getSupertopicList(cookieObj, accountId);
        if (!cards || cards.length === 0) {
            allResults.push({ accountId, success: false, error: '未获取到超话' });
            signResults.push(`⚠️ ${accountId}：未获取到超话数据`); // 带⚠️
            return;
        }

        // 3. 执行签到
        const stats = await processSupertopics(cards, cookieObj, accountId);
        const completionRate = ((stats.checkedInBefore + stats.newlyCheckedIn) / Math.max(stats.totalTopics, 1) * 100).toFixed(1);

        // 输出统计（带表情）
        log('\n========== 签到统计 ==========', 'info', accountId);
        log(`总超话：${stats.totalTopics} 个`, 'info', accountId);
        log(`已签到：${stats.checkedInBefore} 个`, 'info', accountId);
        log(`新签到：${stats.newlyCheckedIn} 个`, 'success', accountId); // 带✅
        log(`失败：${stats.failedCheckin} 个`, stats.failedCheckin > 0 ? 'warn' : 'info', accountId); // 带⚠️/ℹ️
        log(`完成率：${completionRate}%`, 'info', accountId);
        log('===================================\n', 'info', accountId);

        // 汇总结果（带表情）
        allResults.push({ accountId, success: true, stats, completionRate });
        signResults.push(`✅ ${accountId}：完成率${completionRate}%（总${stats.totalTopics}个，新签${stats.newlyCheckedIn}个）`); // 带✅
    } catch (err) {
        const errMsg = `流程异常：${err.message}`;
        log(errMsg, 'error', accountId); // 带❌
        allResults.push({ accountId, success: false, error: errMsg });
        signResults.push(`❌ ${accountId}：${errMsg}`); // 带❌
    }
}

async function main() {
    log('========== 微博超话自动签到程序启动 ==========', 'info');

    // 1. 获取账号
    const accounts = getAccounts();
    if (accounts.length === 0) {
        log('未检测到有效账号，程序退出', 'warn');
        await sendSummary();
        return;
    }

    // 2. 随机延迟（防限流）
    const randomDelay = Math.floor(Math.random() * 3) + 1;
    log(`随机延迟${randomDelay}秒后开始...`, 'info');
    await sleep(randomDelay * 1000);

    // 3. 逐个执行签到
    for (let i = 0; i < accounts.length; i++) {
        await runAccountCheckin(accounts[i]);
        if (i < accounts.length - 1) {
            log(`等待${GLOBAL_CONFIG.ACCOUNT_DELAY / 1000}秒后处理下一个账号...`, 'info');
            await sleep(GLOBAL_CONFIG.ACCOUNT_DELAY);
        }
    }

    // 4. 发送汇总通知（全辅脚本逻辑，带表情）
    await sendSummary();
    log('\n========== 所有签到流程已完成 ==========', 'info');
}

// 启动程序
main();
