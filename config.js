/**
 * AI投资分析助手配置。
 *
 * 安全规则：浏览器端代码不得写入真实API密钥。
 * 需要本地调试时，可在浏览器控制台执行：
 * localStorage.setItem('ZHIPU_API_KEY', '你的临时密钥')
 */

const CONFIG = {
    ZHIPU_API_KEY: localStorage.getItem('ZHIPU_API_KEY') || '',
    ZHIPU_MODEL: 'glm-4.7',
    ZHIPU_MAX_TOKENS: 4096,
    ZHIPU_TEMPERATURE: 0.7,
    ALPHA_VANTAGE_API_KEY: localStorage.getItem('ALPHA_VANTAGE_API_KEY') || '',
    DEFAULT_STOCK: '600519',
    DEFAULT_THEME: 'light',
    LANGUAGE: 'zh-CN',
    ZHIPU_API_ENDPOINT: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    YAHOO_FINANCE_API: 'https://query1.finance.yahoo.com/v8/finance/chart',
    ALPHA_VANTAGE_API: 'https://www.alphavantage.co/query'
};

const SYSTEM_PROMPT = `你是专业、谨慎的投资分析助手。只基于可验证数据进行分析，明确区分事实、推断和不确定性；所有交易建议必须包含风险、仓位、止损和数据时间。分析仅供参考，不构成投资建议。`;

const STOCK_SYMBOLS = {
    '贵州茅台': '600519.SS', '茅台': '600519.SS', '600519': '600519.SS',
    '五粮液': '000858.SZ', '000858': '000858.SZ',
    '中国平安': '601318.SS', '平安': '601318.SS', '601318': '601318.SS',
    '招商银行': '600036.SS', '招行': '600036.SS', '600036': '600036.SS',
    '比亚迪': '002594.SZ', '002594': '002594.SZ',
    '宁德时代': '300750.SZ', '300750': '300750.SZ',
    'Apple': 'AAPL', '苹果': 'AAPL',
    'Microsoft': 'MSFT', '微软': 'MSFT',
    'Tesla': 'TSLA', '特斯拉': 'TSLA',
    'NVIDIA': 'NVDA', '英伟达': 'NVDA',
    '黄金': 'GC=F', 'Gold': 'GC=F', '金价': 'GC=F',
    '原油': 'CL=F', 'Oil': 'CL=F'
};

function getStockSymbol(name) {
    return STOCK_SYMBOLS[name] || name;
}

function formatNumber(num, decimals = 2) {
    return Number.isFinite(Number(num)) ? Number(num).toFixed(decimals) : 'N/A';
}

function formatPercent(num, decimals = 2) {
    if (!Number.isFinite(Number(num))) return 'N/A';
    const value = Number(num);
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

function formatCurrency(num, currency = '¥') {
    if (!Number.isFinite(Number(num))) return 'N/A';
    return currency + Number(num).toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}
