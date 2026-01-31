/**
 * AI投资分析助手 - 工具函数库
 * 提供常用的辅助函数
 */

// ========== DOM操作 ==========

/**
 * 根据ID获取元素
 * @param {string} id - 元素ID
 * @returns {HTMLElement|null}
 */
function $(id) {
    return document.getElementById(id);
}

/**
 * 查询选择器
 * @param {string} selector - CSS选择器
 * @param {HTMLElement} parent - 父元素
 * @returns {HTMLElement|null}
 */
function querySelector(selector, parent = document) {
    return parent.querySelector(selector);
}

/**
 * 查询所有匹配的元素
 * @param {string} selector - CSS选择器
 * @param {HTMLElement} parent - 父元素
 * @returns {NodeList}
 */
function querySelectorAll(selector, parent = document) {
    return parent.querySelectorAll(selector);
}

// ========== 时间和日期 ==========

/**
 * 格式化日期
 * @param {Date|string|number} date - 日期对象、字符串或时间戳
 * @param {string} format - 格式字符串
 * @returns {string} 格式化后的日期字符串
 */
function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');

    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
}

/**
 * 获取当前时间戳
 * @returns {number} 时间戳(毫秒)
 */
function getTimestamp() {
    return Date.now();
}

/**
 * 时间戳转日期
 * @param {number} timestamp - 时间戳(毫秒)
 * @returns {Date} 日期对象
 */
function timestampToDate(timestamp) {
    return new Date(timestamp);
}

// ========== 字符串处理 ==========

/**
 * 截断字符串
 * @param {string} str - 原字符串
 * @param {number} maxLength - 最大长度
 * @param {string} suffix - 后缀(默认为'...')
 * @returns {string} 截断后的字符串
 */
function truncateString(str, maxLength, suffix = '...') {
    if (!str || str.length <= maxLength) return str;
    return str.substring(0, maxLength - suffix.length) + suffix;
}

/**
 * 移除HTML标签
 * @param {string} html - HTML字符串
 * @returns {string} 纯文本字符串
 */
function stripHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
}

/**
 * 转义HTML特殊字符
 * @param {string} str - 原字符串
 * @returns {string} 转义后的字符串
 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * 高亮关键词
 * @param {string} text - 原文本
 * @param {string} keyword - 关键词
 * @returns {string} 高亮后的HTML字符串
 */
function highlightKeyword(text, keyword) {
    if (!keyword) return escapeHtml(text);
    const regex = new RegExp(`(${escapeRegExp(keyword)})`, 'gi');
    return escapeHtml(text).replace(regex, '<mark>$1</mark>');
}

/**
 * 转义正则表达式特殊字符
 * @param {string} str - 字符串
 * @returns {string} 转义后的字符串
 */
function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ========== 数字处理 ==========

/**
 * 格式化数字(添加千分位)
 * @param {number} num - 数字
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的字符串
 */
function formatNumber(num, decimals = 2) {
    if (isNaN(num)) return 'N/A';
    return num.toLocaleString('zh-CN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * 格式化百分比
 * @param {number} num - 数字
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的百分比字符串
 */
function formatPercent(num, decimals = 2) {
    if (isNaN(num)) return 'N/A';
    const sign = num >= 0 ? '+' : '';
    return sign + num.toFixed(decimals) + '%';
}

/**
 * 格式化货币
 * @param {number} num - 数字
 * @param {string} currency - 货币符号
 * @returns {string} 格式化后的货币字符串
 */
function formatCurrency(num, currency = '¥') {
    if (isNaN(num)) return 'N/A';
    return currency + formatNumber(num, 2);
}

/**
 * 限制数字范围
 * @param {number} num - 数字
 * @param {number} min - 最小值
 * @param {number} max - 最大值
 * @returns {number} 限制后的数字
 */
function clamp(num, min, max) {
    return Math.min(Math.max(num, min), max);
}

// ========== 数组处理 ==========

/**
 * 数组去重
 * @param {Array} arr - 数组
 * @returns {Array} 去重后的数组
 */
function uniqueArray(arr) {
    return [...new Set(arr)];
}

/**
 * 数组分组
 * @param {Array} arr - 数组
 * @param {string|Function} key - 分组键或函数
 * @returns {Object} 分组后的对象
 */
function groupBy(arr, key) {
    return arr.reduce((result, item) => {
        const groupKey = typeof key === 'function' ? key(item) : item[key];
        if (!result[groupKey]) {
            result[groupKey] = [];
        }
        result[groupKey].push(item);
        return result;
    }, {});
}

/**
 * 数组排序
 * @param {Array} arr - 数组
 * @param {string|Function} key - 排序键或函数
 * @param {string} order - 排序顺序 ('asc' | 'desc')
 * @returns {Array} 排序后的数组
 */
function sortBy(arr, key, order = 'asc') {
    return arr.slice().sort((a, b) => {
        const aValue = typeof key === 'function' ? key(a) : a[key];
        const bValue = typeof key === 'function' ? key(b) : b[key];

        if (order === 'asc') {
            return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
        } else {
            return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
        }
    });
}

// ========== 对象处理 ==========

/**
 * 深拷贝对象
 * @param {any} obj - 对象
 * @returns {any} 拷贝后的对象
 */
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj);
    if (obj instanceof Array) return obj.map(item => deepClone(item));

    const cloned = {};
    for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
            cloned[key] = deepClone(obj[key]);
        }
    }
    return cloned;
}

/**
 * 合并对象
 * @param {Object} target - 目标对象
 * @param {Object} source - 源对象
 * @returns {Object} 合并后的对象
 */
function mergeObject(target, source) {
    const result = { ...target };
    for (const key in source) {
        if (source.hasOwnProperty(key)) {
            result[key] = source[key];
        }
    }
    return result;
}

/**
 * 获取对象嵌套属性
 * @param {Object} obj - 对象
 * @param {string} path - 属性路径 (如 'a.b.c')
 * @param {any} defaultValue - 默认值
 * @returns {any} 属性值或默认值
 */
function getNestedValue(obj, path, defaultValue = undefined) {
    const keys = path.split('.');
    let result = obj;

    for (const key of keys) {
        if (result === null || result === undefined) {
            return defaultValue;
        }
        result = result[key];
    }

    return result !== undefined ? result : defaultValue;
}

// ========== 验证函数 ==========

/**
 * 验证邮箱格式
 * @param {string} email - 邮箱地址
 * @returns {boolean} 是否有效
 */
function isValidEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

/**
 * 验证股票代码
 * @param {string} code - 股票代码
 * @returns {boolean} 是否有效
 */
function isValidStockCode(code) {
    // A股代码: 6位数字
    const cnStockRegex = /^\d{6}$/;
    // 美股代码: 1-5个大写字母
    const usStockRegex = /^[A-Z]{1,5}$/;
    // 港股代码: 4-5位数字
    const hkStockRegex = /^\d{4,5}$/;

    return cnStockRegex.test(code) ||
           usStockRegex.test(code) ||
           hkStockRegex.test(code);
}

/**
 * 验证URL格式
 * @param {string} url - URL地址
 * @returns {boolean} 是否有效
 */
function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

// ========== 存储函数 ==========

/**
 * 保存到localStorage
 * @param {string} key - 键
 * @param {any} value - 值
 */
function saveToLocalStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        console.error('保存到localStorage失败:', e);
    }
}

/**
 * 从localStorage读取
 * @param {string} key - 键
 * @param {any} defaultValue - 默认值
 * @returns {any} 读取的值或默认值
 */
function getFromLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        console.error('从localStorage读取失败:', e);
        return defaultValue;
    }
}

/**
 * 从localStorage删除
 * @param {string} key - 键
 */
function removeFromLocalStorage(key) {
    try {
        localStorage.removeItem(key);
    } catch (e) {
        console.error('从localStorage删除失败:', e);
    }
}

// ========== 防抖和节流 ==========

/**
 * 防抖函数
 * @param {Function} func - 要执行的函数
 * @param {number} delay - 延迟时间(毫秒)
 * @returns {Function} 防抖后的函数
 */
function debounce(func, delay = 300) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

/**
 * 节流函数
 * @param {Function} func - 要执行的函数
 * @param {number} delay - 延迟时间(毫秒)
 * @returns {Function} 节流后的函数
 */
function throttle(func, delay = 300) {
    let lastTime = 0;
    return function (...args) {
        const now = getTimestamp();
        if (now - lastTime >= delay) {
            lastTime = now;
            func.apply(this, args);
        }
    };
}

// ========== 其他工具函数 ==========

/**
 * 生成UUID
 * @returns {string} UUID字符串
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * 随机数生成
 * @param {number} min - 最小值
 * @param {number} max - 最大值
 * @returns {number} 随机数
 */
function random(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * 延迟执行
 * @param {number} ms - 延迟时间(毫秒)
 * @returns {Promise} Promise对象
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 复制到剪贴板
 * @param {string} text - 要复制的文本
 * @returns {Promise<boolean>} 是否成功
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (e) {
        console.error('复制失败:', e);
        return false;
    }
}

/**
 * 下载文件
 * @param {string} content - 文件内容
 * @param {string} filename - 文件名
 * @param {string} type - MIME类型
 */
function downloadFile(content, filename, type = 'text/plain') {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * 检测移动设备
 * @returns {boolean} 是否是移动设备
 */
function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

/**
 * 获取浏览器信息
 * @returns {Object} 浏览器信息
 */
function getBrowserInfo() {
    const ua = navigator.userAgent;
    let browser = 'Unknown';
    let version = 'Unknown';

    if (ua.indexOf('Chrome') > -1) {
        browser = 'Chrome';
        version = ua.match(/Chrome\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Firefox') > -1) {
        browser = 'Firefox';
        version = ua.match(/Firefox\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Safari') > -1) {
        browser = 'Safari';
        version = ua.match(/Version\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Edge') > -1) {
        browser = 'Edge';
        version = ua.match(/Edge\/(\d+)/)?.[1] || 'Unknown';
    }

    return { browser, version, userAgent: ua };
}
