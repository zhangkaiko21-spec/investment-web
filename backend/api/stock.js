/**
 * 股票数据代理API - 解决CORS跨域问题
 *
 * 用途：前端通过此API间接调用Yahoo Finance，避免浏览器CORS限制
 * 部署：Vercel Serverless Functions
 */

const YAHOO_FINANCE_BASE = 'https://query1.finance.yahoo.com/v8/finance/chart';

/**
 * 获取股票实时行情
 * Query params:
 *   - symbol: 股票代码 (如: 600519.SS, AAPL)
 *   - interval: 时间间隔 (1m, 5m, 1d, 1wk, 1mo)
 *   - range: 时间范围 (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y, max)
 */
export default async function handler(req, res) {
  // 设置CORS头
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Accept');

  // 处理预检请求
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { symbol, interval = '1d', range = '1mo' } = req.query;

    if (!symbol) {
      return res.status(400).json({ error: '缺少股票代码参数 symbol' });
    }

    // 构建Yahoo Finance API URL
    const yahooUrl = `${YAHOO_FINANCE_BASE}/${symbol}?interval=${interval}&range=${range}`;

    console.log(`正在获取股票数据: ${symbol}`);

    // 调用Yahoo Finance API
    const response = await fetch(yahooUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });

    if (!response.ok) {
      throw new Error(`Yahoo Finance API返回错误: ${response.status}`);
    }

    const data = await response.json();

    // 检查数据有效性
    if (!data.chart || !data.chart.result || data.chart.result.length === 0) {
      return res.status(404).json({
        error: '未找到股票数据',
        symbol: symbol,
        hint: '请检查股票代码是否正确'
      });
    }

    const result = data.chart.result[0];
    const meta = result.meta;
    const quotes = result.indicators.quote[0];
    const timestamps = result.timestamp;

    // 格式化返回数据
    const formattedData = {
      meta: {
        symbol: meta.symbol,
        currency: meta.currency,
        exchangeName: meta.exchangeName,
        instrumentType: meta.instrumentType,
        regularMarketPrice: meta.regularMarketPrice,
        previousClose: meta.previousClose,
        regularMarketChange: meta.regularMarketChange,
        regularMarketChangePercent: meta.regularMarketChangePercent,
        regularMarketDayHigh: meta.regularMarketDayHigh,
        regularMarketDayLow: meta.regularMarketDayLow,
        regularMarketVolume: meta.regularMarketVolume,
        fiftyTwoWeekHigh: meta.fiftyTwoWeekHigh,
        fiftyTwoWeekLow: meta.fiftyTwoWeekLow,
        marketCap: meta.marketCap,
      },
      quotes: timestamps.map((ts, index) => ({
        date: new Date(ts * 1000).toISOString(),
        open: quotes.open[index],
        high: quotes.high[index],
        low: quotes.low[index],
        close: quotes.close[index],
        volume: quotes.volume[index],
      })),
      summary: {
        currentPrice: meta.regularMarketPrice,
        change: meta.regularMarketChange,
        changePercent: meta.regularMarketChangePercent,
        high52w: meta.fiftyTwoWeekHigh,
        low52w: meta.fiftyTwoWeekLow,
        marketCap: meta.marketCap,
      }
    };

    // 添加缓存头（减少API调用）
    res.setHeader('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300');

    return res.status(200).json(formattedData);

  } catch (error) {
    console.error('获取股票数据失败:', error);
    return res.status(500).json({
      error: '获取股票数据失败',
      message: error.message,
      hint: '请稍后重试或联系管理员'
    });
  }
}
