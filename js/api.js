/**
 * AI投资分析助手 - API调用模块
 * 负责与Claude API和股票数据API交互
 */

// ========== Claude API ==========

/**
 * 调用智谱AI API获取回复
 * @param {string} message - 用户消息
 * @param {Array} history - 聊天历史
 * @returns {Promise<string>} AI回复
 */
async function callClaudeAPI(message, history = []) {
    try {
        // 构建消息数组
        const messages = [
            {
                role: 'system',
                content: SYSTEM_PROMPT
            },
            {
                role: 'user',
                content: message
            }
        ];

        // 添加历史消息（最近20条）
        const recentHistory = history.slice(-20);
        recentHistory.forEach((item) => {
            messages.push({
                role: item.role === 'assistant' ? 'assistant' : 'user',
                content: item.content
            });
        });

        const response = await fetch(CONFIG.ZHIPU_API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${CONFIG.ZHIPU_API_KEY}`
            },
            body: JSON.stringify({
                model: CONFIG.ZHIPU_MODEL,
                messages: messages,
                max_tokens: CONFIG.ZHIPU_MAX_TOKENS,
                temperature: CONFIG.ZHIPU_TEMPERATURE,
                stream: false
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`智谱AI API错误: ${errorData.error?.message || response.statusText}`);
        }

        const data = await response.json();

        // 智谱AI返回格式: choices[0].message.content
        if (data.choices && data.choices[0] && data.choices[0].message) {
            return data.choices[0].message.content;
        } else {
            throw new Error('智谱AI返回数据格式错误');
        }

    } catch (error) {
        console.error('调用智谱AI API失败:', error);
        throw error;
    }
}

// ========== 股票数据API ==========

/**
 * 使用Yahoo Finance API获取股票数据
 * @param {string} symbol - 股票代码
 * @param {string} interval - 时间间隔 ('1d', '1wk', '1mo')
 * @param {string} range - 时间范围 ('1d', '5d', '1mo', '3mo', '6mo', '1y', 'max')
 * @returns {Promise<Object>} 股票数据
 */
async function getStockDataYahoo(symbol, interval = '1d', range = '1mo') {
    try {
        const response = await fetch(
            `${CONFIG.YAHOO_FINANCE_API}/${symbol}?interval=${interval}&range=${range}`
        );

        if (!response.ok) {
            throw new Error(`Yahoo Finance API错误: ${response.statusText}`);
        }

        const data = await response.json();

        // 检查数据有效性
        if (!data.chart?.result?.[0]) {
            throw new Error('无法获取股票数据');
        }

        const result = data.chart.result[0];
        const meta = result.meta;
        const quotes = result.indicators.quote[0];
        const timestamps = result.timestamp;

        return {
            symbol: symbol,
            name: meta.longName || symbol,
            currentPrice: meta.regularMarketPrice || meta.previousClose,
            previousClose: meta.previousClose,
            change: meta.regularMarketPrice - meta.previousClose,
            changePercent: ((meta.regularMarketPrice - meta.previousClose) / meta.previousClose) * 100,
            high: meta.regularMarketDayHigh,
            low: meta.regularMarketDayLow,
            volume: meta.regularMarketVolume,

            // 历史数据
            timestamps: timestamps,
            open: quotes.open,
            high: quotes.high,
            low: quotes.low,
            close: quotes.close,
            volume: quotes.volume,

            // 元数据
            currency: meta.currency,
            exchangeName: meta.exchangeName,
            marketState: meta.marketState
        };

    } catch (error) {
        console.error('获取Yahoo Finance数据失败:', error);
        throw error;
    }
}

/**
 * 使用Alpha Vantage API获取股票数据
 * @param {string} symbol - 股票代码
 * @param {string} function - API函数 ('GLOBAL_QUOTE', 'TIME_SERIES_DAILY', etc.)
 * @returns {Promise<Object>} 股票数据
 */
async function getStockDataAlphaVantage(symbol, functionType = 'GLOBAL_QUOTE') {
    try {
        if (!CONFIG.ALPHA_VANTAGE_API_KEY || CONFIG.ALPHA_VANTAGE_API_KEY === 'YOUR_ALPHA_VANTAGE_KEY_HERE') {
            console.warn('Alpha Vantage API密钥未配置');
            return null;
        }

        const response = await fetch(
            `${CONFIG.ALPHA_VANTAGE_API}?function=${functionType}&symbol=${symbol}&apikey=${CONFIG.ALPHA_VANTAGE_API_KEY}`
        );

        if (!response.ok) {
            throw new Error(`Alpha Vantage API错误: ${response.statusText}`);
        }

        const data = await response.json();

        // 检查错误信息
        if (data['Error Message']) {
            throw new Error(data['Error Message']);
        }

        if (data['Note']) {
            throw new Error('API调用频率限制，请稍后再试');
        }

        return data;

    } catch (error) {
        console.error('获取Alpha Vantage数据失败:', error);
        throw error;
    }
}

/**
 * 获取实时股价
 * @param {string} symbol - 股票代码
 * @returns {Promise<Object>} 股价信息
 */
async function getRealTimePrice(symbol) {
    try {
        // 优先使用Yahoo Finance
        const data = await getStockDataYahoo(symbol, '1d', '5d');

        return {
            symbol: data.symbol,
            name: data.name,
            price: data.currentPrice,
            change: data.change,
            changePercent: data.changePercent,
            high: data.high,
            low: data.low,
            volume: data.volume,
            currency: data.currency,
            exchange: data.exchangeName,
            marketState: data.marketState,
            timestamp: new Date().toISOString()
        };

    } catch (error) {
        console.error('获取实时股价失败:', error);

        // 如果Yahoo失败，尝试Alpha Vantage
        try {
            const avData = await getStockDataAlphaVantage(symbol, 'GLOBAL_QUOTE');
            const quote = avData['Global Quote'];

            return {
                symbol: quote['01. symbol'],
                price: parseFloat(quote['05. price']),
                change: parseFloat(quote['09. change']),
                changePercent: parseFloat(quote['10. change percent'].replace('%', '')),
                high: parseFloat(quote['03. high']),
                low: parseFloat(quote['04. low']),
                volume: parseInt(quote['06. volume']),
                timestamp: quote['07. latest trading day']
            };

        } catch (avError) {
            console.error('Alpha Vantage也失败了:', avError);
            throw new Error('无法获取股价数据');
        }
    }
}

/**
 * 获取股票历史K线数据
 * @param {string} symbol - 股票代码
 * @param {string} interval - 时间间隔
 * @param {string} range - 时间范围
 * @returns {Promise<Array>} K线数据
 */
async function getStockCandlestick(symbol, interval = '1d', range = '1mo') {
    try {
        const data = await getStockDataYahoo(symbol, interval, range);

        // 转换为图表所需的格式
        const candlestickData = [];
        const timestamps = data.timestamps || [];
        const open = data.open || [];
        const high = data.high || [];
        const low = data.low || [];
        const close = data.close || [];
        const volume = data.volume || [];

        for (let i = 0; i < timestamps.length; i++) {
            candlestickData.push({
                x: timestamps[i] * 1000, // 转换为毫秒
                o: open[i],
                h: high[i],
                l: low[i],
                c: close[i],
                v: volume[i]
            });
        }

        return {
            symbol: data.symbol,
            name: data.name,
            data: candlestickData
        };

    } catch (error) {
        console.error('获取K线数据失败:', error);
        throw error;
    }
}

// ========== 黄金价格API ==========

/**
 * 获取黄金价格
 * @returns {Promise<Object>} 黄金价格信息
 */
async function getGoldPrice() {
    try {
        return await getRealTimePrice('GC=F'); // 黄金期货
    } catch (error) {
        console.error('获取金价失败:', error);
        throw error;
    }
}

// ========== 新闻API ==========

/**
 * 搜索股票相关新闻
 * @param {string} query - 搜索关键词
 * @returns {Promise<Array>} 新闻列表
 */
async function searchStockNews(query) {
    // 注意：这里可以集成新闻API
    // 由于CORS限制，这里返回模拟数据
    // 实际部署时可以使用后端代理或使用支持CORS的API

    return {
        query: query,
        news: [],
        timestamp: new Date().toISOString()
    };
}

// ========== 工具函数 ==========

/**
 * 识别股票代码
 * @param {string} text - 文本
 * @returns {Array<string>} 股票代码列表
 */
function identifyStockCodes(text) {
    const codes = [];

    // 匹配6位数字(A股代码)
    const cnCodeMatch = text.match(/\b\d{6}\b/g);
    if (cnCodeMatch) {
        codes.push(...cnCodeMatch);
    }

    // 匹配股票名称(从预定义列表中查找)
    for (const [name, code] of Object.entries(STOCK_SYMBOLS)) {
        if (text.includes(name)) {
            codes.push(code);
        }
    }

    return uniqueArray(codes);
}

/**
 * 预处理用户消息
 * @param {string} message - 原始消息
 * @returns {string} 处理后的消息
 */
function preprocessMessage(message) {
    let processed = message.trim();

    // 识别并转换股票代码
    const codes = identifyStockCodes(processed);

    // 如果检测到股票代码，添加到消息中
    if (codes.length > 0) {
        processed += `\n\n检测到股票代码: ${codes.join(', ')}`;
    }

    return processed;
}

// ========== 错误处理 ==========

/**
 * 处理API错误
 * @param {Error} error - 错误对象
 * @returns {string} 用户友好的错误消息
 */
function handleAPIError(error) {
    console.error('API错误:', error);

    if (error.message.includes('401') || error.message.includes('403')) {
        return '❌ 智谱AI密钥无效或已过期，请检查config.js中的配置。';
    } else if (error.message.includes('429') || error.message.includes('频率限制')) {
        return '❌ API调用频率超限，请稍后再试。';
    } else if (error.message.includes('余额') || error.message.includes('额度')) {
        return '❌ API余额不足，请充值智谱AI账户。';
    } else if (error.message.includes('500') || error.message.includes('502')) {
        return '❌ 服务器错误，请稍后再试。';
    } else if (error.message.includes('network') || error.message.includes('fetch')) {
        return '❌ 网络错误，请检查网络连接。';
    } else {
        return `❌ 发生错误: ${error.message}`;
    }
}

// ========== 导出函数 ==========

// 将函数暴露到全局作用域
window.callClaudeAPI = callClaudeAPI;
window.getStockDataYahoo = getStockDataYahoo;
window.getStockDataAlphaVantage = getStockDataAlphaVantage;
window.getRealTimePrice = getRealTimePrice;
window.getStockCandlestick = getStockCandlestick;
window.getGoldPrice = getGoldPrice;
window.searchStockNews = searchStockNews;
window.identifyStockCodes = identifyStockCodes;
window.preprocessMessage = preprocessMessage;
window.handleAPIError = handleAPIError;
