/**
 * AI投资分析助手 - 主逻辑模块
 * 负责应用的核心流程和交互逻辑
 */

// ========== 全局变量 ==========

let chatHistory = []; // 聊天历史
let isProcessing = false; // 是否正在处理
let currentStockData = null; // 当前股票数据

// ========== 初始化 ==========

/**
 * 初始化应用
 */
function initApp() {
    console.log('AI投资分析助手启动中...');

    // 检查配置
    checkConfig();

    // 加载历史记录
    loadChatHistory();

    // 绑定事件
    bindEvents();

    // 设置默认主题
    setTheme(CONFIG.DEFAULT_THEME);

    console.log('AI投资分析助手已启动');
}

/**
 * 检查配置
 */
function checkConfig() {
    if (CONFIG.CLAUDE_API_KEY === 'YOUR_CLAUDE_API_KEY_HERE') {
        showMessage('assistant', '⚠️ 请先在config.js中配置您的Claude API密钥！<br><br>您可以从 https://console.anthropic.com/ 获取API密钥。');
        return false;
    }
    return true;
}

/**
 * 绑定事件监听器
 */
function bindEvents() {
    // 发送按钮
    const sendBtn = $('sendButton');
    if (sendBtn) {
        sendBtn.addEventListener('click', handleSendMessage);
    }

    // 输入框回车发送
    const userInput = $('userInput');
    if (userInput) {
        userInput.addEventListener('keydown', function(e) {
            // Enter发送，Shift+Enter换行
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });

        // 自动调整高度
        userInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }

    // 示例问题点击
    const exampleQuestions = querySelectorAll('.example-questions li');
    exampleQuestions.forEach(q => {
        q.addEventListener('click', function() {
            $('userInput').value = this.textContent;
            handleSendMessage();
        });
    });
}

// ========== 消息处理 ==========

/**
 * 发送消息处理
 */
async function handleSendMessage() {
    // 防止重复提交
    if (isProcessing) return;

    const userInput = $('userInput');
    const message = userInput.value.trim();

    if (!message) return;

    // 清空输入框
    userInput.value = '';
    userInput.style.height = 'auto';

    // 显示用户消息
    showMessage('user', message);
    addToHistory('user', message);

    // 显示加载状态
    showLoading();
    isProcessing = true;

    try {
        // 识别股票代码
        const stockCodes = identifyStockCodes(message);

        // 如果检测到股票代码，先获取数据
        if (stockCodes.length > 0) {
            try {
                const stockCode = stockCodes[0];
                const stockData = await getRealTimePrice(stockCode);
                currentStockData = stockData;

                // 在消息中添加股票数据
                const stockInfo = formatStockInfo(stockData);
                showMessage('assistant', stockInfo + '\n\n正在分析...');

                // 提供查看图表的按钮
                addChartButton(stockData);

            } catch (error) {
                console.error('获取股票数据失败:', error);
                showMessage('assistant', `⚠️ 无法获取股票数据: ${error.message}\n\n继续使用AI分析...`);
            }
        }

        // 调用Claude API
        const response = await callClaudeAPI(message, chatHistory);

        // 显示AI回复
        showMessage('assistant', response);
        addToHistory('assistant', response);

        // 如果有股票数据，显示图表
        if (currentStockData) {
            try {
                const chartData = await getStockCandlestick(currentStockData.symbol);
                // 不自动显示图表，而是添加按钮让用户选择
            } catch (error) {
                console.error('获取图表数据失败:', error);
            }
        }

    } catch (error) {
        console.error('处理失败:', error);
        const errorMsg = handleAPIError(error);
        showMessage('assistant', errorMsg);
    } finally {
        hideLoading();
        isProcessing = false;
    }
}

/**
 * 显示消息
 * @param {string} role - 角色 ('user' | 'assistant')
 * @param {string} content - 消息内容
 */
function showMessage(role, content) {
    const chatMessages = $('chatMessages');
    if (!chatMessages) return;

    // 创建消息元素
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    // 创建头像
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    const avatarIcon = document.createElement('span');
    avatarIcon.className = 'avatar-icon';
    avatarIcon.textContent = role === 'user' ? '👤' : '🤖';
    avatarDiv.appendChild(avatarIcon);

    // 创建内容区
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';

    // 处理Markdown和换行
    textDiv.innerHTML = formatMessage(content);

    contentDiv.appendChild(textDiv);

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);

    // 滚动到底部
    scrollToBottom();
}

/**
 * 格式化消息内容
 * @param {string} content - 原始内容
 * @returns {string} 格式化后的HTML
 */
function formatMessage(content) {
    // 转义HTML
    let formatted = escapeHtml(content);

    // 处理代码块
    formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, function(match, lang, code) {
        return `<pre><code class="language-${lang}">${code}</code></pre>`;
    });

    // 处理行内代码
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 处理换行
    formatted = formatted.replace(/\n/g, '<br>');

    // 处理加粗
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 处理链接
    formatted = formatted.replace(/https?:\/\/[^\s]+/g, function(url) {
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
    });

    return formatted;
}

/**
 * 格式化股票信息
 * @param {Object} stockData - 股票数据
 * @returns {string} 格式化后的股票信息
 */
function formatStockInfo(stockData) {
    const changeSign = stockData.change >= 0 ? '+' : '';
    const changeColor = stockData.change >= 0 ? '📈' : '📉';

    return `📊 ${stockData.name || stockData.symbol}
${changeColor} 价格: ${formatCurrency(stockData.price, stockData.currency || '¥')}
涨跌: ${changeSign}${formatCurrency(stockData.change)} (${changeSign}${stockData.changePercent.toFixed(2)}%)
今日最高: ${formatCurrency(stockData.high)}
今日最低: ${formatCurrency(stockData.low)}
成交量: ${formatNumber(stockData.volume)}`;
}

/**
 * 添加图表按钮
 * @param {Object} stockData - 股票数据
 */
function addChartButton(stockData) {
    const chatMessages = $('chatMessages');
    const lastMessage = chatMessages.lastElementChild;

    if (!lastMessage) return;

    // 创建按钮容器
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'chart-buttons';
    buttonContainer.style.cssText = 'display: flex; gap: 10px; margin-top: 10px;';

    // K线图按钮
    const candlestickBtn = createChartButton('📊 K线图', () => {
        getStockCandlestick(stockData.symbol)
            .then(data => showChartInModal(data, 'candlestick'))
            .catch(err => console.error('获取K线数据失败:', err));
    });

    // 分时图按钮
    const timeseriesBtn = createChartButton('📈 分时图', () => {
        getStockCandlestick(stockData.symbol, '1m', '1d')
            .then(data => showChartInModal(data, 'timeseries'))
            .catch(err => console.error('获取分时数据失败:', err));
    });

    // 组合图按钮
    const combinedBtn = createChartButton('📉 组合图', () => {
        getStockCandlestick(stockData.symbol)
            .then(data => showChartInModal(data, 'combined'))
            .catch(err => console.error('获取组合数据失败:', err));
    });

    buttonContainer.appendChild(candlestickBtn);
    buttonContainer.appendChild(timeseriesBtn);
    buttonContainer.appendChild(combinedBtn);

    lastMessage.querySelector('.message-content').appendChild(buttonContainer);
}

/**
 * 创建图表按钮
 * @param {string} text - 按钮文本
 * @param {Function} onClick - 点击事件
 * @returns {HTMLElement} 按钮元素
 */
function createChartButton(text, onClick) {
    const button = document.createElement('button');
    button.textContent = text;
    button.style.cssText = `
        padding: 8px 16px;
        border: none;
        border-radius: 8px;
        background: linear-gradient(135deg, var(--primary-color) 0%, #7c3aed 100%);
        color: white;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s;
    `;

    button.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
        this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    });

    button.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = 'none';
    });

    button.addEventListener('click', onClick);

    return button;
}

// ========== 历史记录 ==========

/**
 * 添加到历史记录
 * @param {string} role - 角色
 * @param {string} content - 内容
 */
function addToHistory(role, content) {
    chatHistory.push({
        role: role,
        content: content,
        timestamp: new Date().toISOString()
    });

    // 限制历史记录数量（最多保留50条）
    if (chatHistory.length > 50) {
        chatHistory = chatHistory.slice(-50);
    }

    // 保存到localStorage
    saveToLocalStorage('chatHistory', chatHistory);
}

/**
 * 加载历史记录
 */
function loadChatHistory() {
    const saved = getFromLocalStorage('chatHistory', []);
    chatHistory = saved;
}

/**
 * 清空历史记录
 */
function clearHistory() {
    chatHistory = [];
    removeFromLocalStorage('chatHistory');
}

// ========== 加载状态 ==========

/**
 * 显示加载状态
 */
function showLoading() {
    const loading = $('loadingOverlay');
    if (loading) {
        loading.classList.add('active');
    }
}

/**
 * 隐藏加载状态
 */
function hideLoading() {
    const loading = $('loadingOverlay');
    if (loading) {
        loading.classList.remove('active');
    }
}

// ========== 滚动控制 ==========

/**
 * 滚动到底部
 */
function scrollToBottom() {
    const chatMessages = $('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// ========== 主题切换 ==========

/**
 * 设置主题
 * @param {string} theme - 主题 ('light' | 'dark')
 */
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    saveToLocalStorage('theme', theme);
}

/**
 * 切换主题
 */
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'light' ? 'dark' : 'light');
}

// ========== 工具函数 ==========

/**
 * 快捷提问
 * @param {string} question - 问题
 */
function quickAsk(question) {
    $('userInput').value = question;
    handleSendMessage();
}

// ========== 导出 ==========

window.initApp = initApp;
window.handleSendMessage = handleSendMessage;
window.showMessage = showMessage;
window.quickAsk = quickAsk;
window.toggleTheme = toggleTheme;
window.clearHistory = clearHistory;

// ========== 启动应用 ==========

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', initApp);

// 页面卸载前保存状态
window.addEventListener('beforeunload', function() {
    saveToLocalStorage('chatHistory', chatHistory);
});
