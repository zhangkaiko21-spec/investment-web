# Backend - 股票数据代理服务

## 📁 目录结构

```
backend/
├── api/
│   └── stock.js          # 股票数据API端点（Vercel Serverless Function）
├── package.json          # 项目依赖配置
├── vercel.json           # Vercel部署配置
└── README.md             # 本文件
```

## 🎯 功能说明

### api/stock.js

这是一个Vercel Serverless Function，作为前端和Yahoo Finance API之间的代理。

**为什么需要代理？**
- 浏览器的CORS安全策略阻止直接调用Yahoo Finance API
- 服务器端（后端）可以调用任何API，没有CORS限制
- 后端作为"中间人"，帮助前端获取数据

**支持的功能：**
- ✅ 获取实时股价
- ✅ 获取历史K线数据
- ✅ 支持A股、美股、港股等全球股票
- ✅ 支持黄金、原油等大宗商品
- ✅ 自动缓存，减少API调用

## 🔧 本地测试

### 前置要求

- Node.js >= 18.0.0
- npm 或 yarn

### 安装依赖

```bash
cd backend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问: http://localhost:3000/api/stock?symbol=600519.SS

## 🚀 部署到Vercel

### 快速部署

1. **推送到GitHub**
   ```bash
   git add backend/
   git commit -m "添加后端API服务"
   git push
   ```

2. **在Vercel导入项目**
   - 访问: https://vercel.com/dashboard
   - 点击 "Add New" → "Project"
   - 选择 `investment-web` 仓库
   - 设置 Root Directory 为 `backend`
   - 点击 "Deploy"

3. **获取API地址**
   部署完成后，地址为：
   ```
   https://your-project.vercel.app/api/stock
   ```

### 环境变量（可选）

如果需要配置环境变量：

1. 在Vercel项目页面
2. 点击 "Settings" → "Environment Variables"
3. 添加变量：
   - `NODE_ENV`: `production`
   - `CACHE_MAX_AGE`: `60` (缓存秒数)

## 📡 API使用说明

### 端点

```
GET /api/stock
```

### 查询参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|:---|:---:|:---:|:---|:---|
| `symbol` | string | ✅ | 股票代码 | `600519.SS`, `AAPL`, `0700.HK` |
| `interval` | string | ❌ | 时间间隔 | `1m`, `5m`, `1d`, `1wk`, `1mo` (默认: `1d`) |
| `range` | string | ❌ | 时间范围 | `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `max` (默认: `1mo`) |

### 股票代码格式

| 市场 | 格式 | 示例 |
|:---|:---|:---|
| **A股上海** | `{代码}.SS` | `600519.SS` (贵州茅台) |
| **A股深圳** | `{代码}.SZ` | `000858.SZ` (五粮液) |
| **港股** | `{代码}.HK` | `0700.HK` (腾讯) |
| **美股** | `{代码}` | `AAPL`, `TSLA`, `NVDA` |
| **黄金期货** | `GC=F` | `GC=F` |
| **原油期货** | `CL=F` | `CL=F` |

### 请求示例

```bash
# 获取贵州茅台最近1个月数据
curl "https://your-project.vercel.app/api/stock?symbol=600519.SS&interval=1d&range=1mo"

# 获取苹果股票最近5天数据
curl "https://your-project.vercel.app/api/stock?symbol=AAPL&interval=1d&range=5d"

# 获取黄金价格
curl "https://your-project.vercel.app/api/stock?symbol=GC=F&interval=1d&range=5d"
```

### 响应格式

```json
{
  "meta": {
    "symbol": "600519.SS",
    "currency": "CNY",
    "exchangeName": "SHH",
    "instrumentType": "EQUITY",
    "regularMarketPrice": 1680.50,
    "previousClose": 1640.00,
    "regularMarketChange": 40.50,
    "regularMarketChangePercent": 2.47,
    "regularMarketDayHigh": 1685.00,
    "regularMarketDayLow": 1648.00,
    "regularMarketVolume": 2500000,
    "fiftyTwoWeekHigh": 1850.00,
    "fiftyTwoWeekLow": 1450.00,
    "marketCap": 2100000000000
  },
  "quotes": [
    {
      "date": "2025-01-27T00:00:00.000Z",
      "open": 1650.00,
      "high": 1685.00,
      "low": 1648.00,
      "close": 1680.50,
      "volume": 2500000
    }
  ],
  "summary": {
    "currentPrice": 1680.50,
    "change": 40.50,
    "changePercent": 2.47,
    "high52w": 1850.00,
    "low52w": 1450.00,
    "marketCap": 2100000000000
  }
}
```

## 🔒 安全说明

### CORS配置

默认配置允许所有域名访问 (`Access-Control-Allow-Origin: *`)。

**如果需要限制访问**，修改 `api/stock.js`：

```javascript
// 只允许特定域名
res.setHeader('Access-Control-Allow-Origin', 'https://your-username.github.io');
```

### 速率限制

Vercel自动提供基本的速率限制。

**如需自定义**，可以在 `vercel.json` 中添加：

```json
{
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/$1",
      "methods": ["GET"],
      "maxRate": 10 // 每秒最多10个请求
    }
  ]
}
```

## 📊 性能优化

### 缓存策略

默认配置了HTTP缓存：

```javascript
res.setHeader('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300');
```

**说明**：
- `s-maxage=60`: 缓存60秒
- `stale-while-revalidate=300`: 缓存过期后，返回旧数据的同时后台更新

### 成本优化

**Vercel免费额度**：
- 带宽: 100GB/月
- Serverless执行: 100GB-小时/月

**个人使用估算**：
- 每天查询20次股票
- 每次响应约50KB
- 每月带宽: 20 × 50KB × 30 = 30MB ✅ 远低于限额
- 每月执行时间: 20 × 0.5秒 × 30 = 5分钟 ✅ 远低于限额

**结论**: 完全免费使用！

## 🐛 故障排查

### 问题1: 部署失败

**检查项**:
- [ ] `Root Directory` 设置为 `backend`
- [ ] `package.json` 文件存在
- [ ] Node.js版本 >= 18.0.0

### 问题2: API返回404

**检查项**:
- [ ] URL路径正确：`/api/stock`
- [ ] 查询参数正确：`?symbol=xxx`
- [ ] 股票代码格式正确

### 问题3: 获取数据失败

**检查项**:
- [ ] Yahoo Finance API可访问
- [ ] 网络连接正常
- [ ] 股票代码存在

## 📝 开发说明

### 添加新的API端点

1. 在 `backend/api/` 创建新文件
2. 导出默认函数：
   ```javascript
   export default async function handler(req, res) {
     // 处理逻辑
   }
   ```
3. 重新部署

### 修改配置

- **超时时间**: 在函数中设置
- **缓存策略**: 修改 `Cache-Control` 头
- **错误处理**: 修改错误响应格式

## 📚 相关资源

### 官方文档

- [Vercel Serverless Functions](https://vercel.com/docs/functions/serverless-functions)
- [Vercel Configuration](https://vercel.com/docs/projects/project-configuration)
- [Yahoo Finance API](https://query1.finance.yahoo.com/v8/finance/chart/)

### 项目文档

- [前端部署指南](../DEPLOYMENT_GUIDE.md)
- [后端部署指南](../BACKEND_DEPLOYMENT_GUIDE.md)
- [主README](../README.md)

---

**最后更新**: 2026-01-31
**版本**: 1.0.0
