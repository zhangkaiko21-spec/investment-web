# 💼 AI投资分析助手 - 网页版

> 基于Claude AI的专业投资分析系统，27项核心能力，零成本部署

![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-32773a?logo=github)
![Claude AI](https://img.shields.io/badge/Claude-AI-cc785c?logo=anthropic)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ 特性

- 🤖 **AI驱动** - 基于Claude AI，具备27项专业投资分析能力
- 💬 **对话界面** - ChatGPT风格的聊天界面，自然流畅
- 📊 **实时行情** - 支持A股、美股、黄金实时数据查询
- 📈 **图表展示** - K线图、分时图、组合图等多种图表
- 🌍 **公网访问** - 部署到GitHub Pages，全球可访问
- 💰 **零成本** - 完全免费，无服务器维护成本
- 📱 **响应式设计** - 支持手机、平板、电脑访问

---

## 🚀 快速开始

### 5分钟部署指南

#### Step 1: 准备工作

1. **注册GitHub账号** (如果没有)
   - 访问: https://github.com/
   - 点击"Sign up"免费注册

2. **获取智谱AI API密钥** (如果没有)
   - 访问: https://open.bigmodel.cn/
   - 注册并获取API密钥
   - 新用户通常有免费额度

#### Step 2: 配置项目

1. **下载项目文件**
   - 下载所有文件到本地
   - 或使用git克隆此仓库

2. **配置API密钥**

   打开 `config.js` 文件，找到以下行：

   ```javascript
   ZHIPU_API_KEY: '6c17c076f2934c50a09a21dae5195c33.RfWC2RgrZN0IpfOE',
   ```

   如果您使用的是自己的密钥，替换为您的实际API密钥：

   ```javascript
   ZHIPU_API_KEY: 'your-api-key-here',
   ```

3. **（可选）配置Alpha Vantage API** (用于美股数据)

   - 访问: https://www.alphavantage.co/support/#api-key
   - 免费获取API密钥
   - 在config.js中配置：

   ```javascript
   ALPHA_VANTAGE_API_KEY: 'YOUR_KEY',
   ```

#### Step 3: 上传到GitHub

**方式1: 使用网页上传 (最简单)**

1. 登录GitHub
2. 点击右上角 "+" → "New repository"
3. 仓库名称: `investment-web`
4. 设置为Public (公开)
5. 点击"Create repository"
6. 点击"uploading an existing file"
7. 拖拽所有项目文件到上传区域
8. 点击"Commit changes"

**方式2: 使用Git命令**

```bash
# 初始化git仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit"

# 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/investment-web.git

# 推送到GitHub
git push -u origin main
```

#### Step 4: 启用GitHub Pages

1. 进入仓库页面
2. 点击 "Settings" (设置)
3. 左侧菜单找到 "Pages"
4. 在 "Source" 下选择:
   - Branch: `main`
   - Folder: `/root`
5. 点击 "Save"

#### Step 5: 访问网站

等待1-2分钟后，访问：

```
https://YOUR_USERNAME.github.io/investment-web/
```

将 `YOUR_USERNAME` 替换为您的GitHub用户名。

---

## 📖 使用说明

### 基本使用

1. **输入问题**
   - 在输入框中输入您的问题
   - 例如: "分析一下贵州茅台"
   - 按Enter发送 (Shift+Enter换行)

2. **查看回复**
   - AI会给出专业的投资分析
   - 包含技术面、基本面、新闻情感等
   - 自动添加风险提示

3. **查看图表**
   - 如果涉及股票，会显示图表按钮
   - 点击按钮查看K线图、分时图等
   - 支持缩放和交互

### 示例问题

#### A股分析
```
分析一下贵州茅台
五粮液值得买吗？
600519技术面怎么样？
```

#### 美股分析
```
Analyze Apple stock
特斯拉值得投资吗？
Microsoft怎么样？
```

#### 黄金分析
```
金价今天怎么样？
黄金现在是买入时机吗？
金价会涨到多少？
```

#### 全球事件
```
今天有什么大事？
美联储加息对股市有什么影响？
地缘政治对黄金的影响？
```

### 高级功能

**1. 查看K线图**
- 点击 "📊 K线图" 按钮
- 查看蜡烛图走势
- 支持鼠标悬停查看详情

**2. 查看分时图**
- 点击 "📈 分时图" 按钮
- 查看当日价格走势
- 适合短线交易分析

**3. 查看组合图**
- 点击 "📉 组合图" 按钮
- 同时显示价格和成交量
- 综合分析更全面

**4. 切换主题**
- 深色模式 / 浅色模式
- 保护眼睛，适合夜间使用

---

## 📁 项目结构

```
investment-web/
├── index.html          # 主页面
├── config.js           # 配置文件 (需修改API密钥)
├── css/
│   └── style.css      # 样式文件
├── js/
│   ├── app.js         # 主逻辑
│   ├── api.js         # API调用
│   ├── chart.js       # 图表绘制
│   └── utils.js       # 工具函数
└── README.md          # 使用说明
```

---

## ⚙️ 配置说明

### config.js 主要配置

```javascript
const CONFIG = {
    // 智谱AI API配置 (必填)
    ZHIPU_API_KEY: 'your-api-key-here',

    // 智谱AI API设置
    ZHIPU_MODEL: 'glm-4-plus',  // 或 'glm-4-flash' (更快速)
    ZHIPU_MAX_TOKENS: 4096,
    ZHIPU_TEMPERATURE: 0.7,

    // Alpha Vantage配置 (可选，用于美股)
    ALPHA_VANTAGE_API_KEY: 'YOUR_KEY_HERE',

    // 默认设置
    DEFAULT_STOCK: '600519',  // 默认股票
    DEFAULT_THEME: 'light',   // 默认主题
    LANGUAGE: 'zh-CN',        // 语言
};
```

---

## 💡 功能说明

### 27项投资分析能力

1. **中国股票分析** - A股技术面+基本面+新闻情感
2. **美国股票分析** - 美股三大指数+个股分析
3. **全球新闻追踪** - 地缘政治、央行政策、重大经济数据
4. **资源市场分析** - 黄金、原油、大宗商品
5. **全球大事件实时监控** - 及时提醒重大全球事件
6. **独立理性分析** - 不受媒体影响，只基于事实和逻辑
7. **影响分析矩阵** - 明确利好/利空影响
8. **操作建议系统** - 具体可执行的买卖建议
9. **24小时金价监控** - 实时追踪国际金价
10. **异常波动检测** - 自动识别≥2%波动
11. **即时响应系统** - 立即分析+操作建议
12. **人性分析系统** - 识别市场情绪极端，逆向投资机会
13. **长远视角系统** - 10年+产业趋势，代际变化洞察
14. **周期分析系统** - 基钦/朱格拉/康波周期规律
15. **风险管理系统** - 七大风险识别与全面控制
16. **投资者心理建设** - 心态修炼、纪律养成、认知升级
17. **护城河分析** - 八大竞争优势识别与评估
18. **资产配置系统** - 战略与战术配置，决定90%回报
19. **交易系统** - 买卖信号、仓位管理、执行纪律
20. **学习进化系统** - 知识管理、持续学习、能力提升
21. **估值深化模块** - DCF、DDM、相对估值完整框架
22. **财报分析深化** - 三大报表、财务健康度、造假识别
23. **国际宏观分析** - 全球经济、货币政策、资本流动
24. **期权与衍生品** - 期权基础、风险警示（高风险警告）
25. **房地产投资** - 买房vs租房、租售比、房产估值
26. **加密资产** - 风险警示、骗局识别（赌博性质警告）
27. **债券深度分析** - 国债、金融债、企业债、债券策略

---

## 🔧 技术栈

- **前端**: HTML5, CSS3, JavaScript (ES6+)
- **图表**: Chart.js 4.4.0
- **托管**: GitHub Pages
- **AI**: 智谱AI API (Zhipu AI / GLM-4)
- **数据源**:
  - Yahoo Finance API (免费)
  - Alpha Vantage API (免费，可选)

---

## 💰 成本分析

### 完全免费

| 项目 | 费用 | 说明 |
|:---|:---:|:---|
| GitHub托管 | ¥0/月 | 无限流量，永久免费 |
| 域名 | ¥0/年 | github.io子域名免费 |
| Yahoo Finance API | ¥0/月 | 完全免费 |
| Chart.js | ¥0 | 开源库 |
| Alpha Vantage | ¥0/月 | 每日500次免费 (可选) |

### 智谱AI API费用

- **免费额度**: 新用户通常有免费额度
- **按量付费**:
  - GLM-4-Plus: ¥0.05/千tokens
  - GLM-4-Flash: ¥0.001/千tokens (更便宜)
  - 日常使用估算: ¥5-50/月

---

## ⚠️ 安全注意事项

### API密钥保护

由于是纯前端方案，API密钥会暴露在网页代码中。建议：

1. **设置使用限额**
   - 在Anthropic控制台设置每月限额
   - 避免被盗用产生高额费用

2. **定期轮换密钥**
   - 每月更换一次API密钥
   - 发现异常立即更换

3. **仅限个人使用**
   - 不要公开分享网站链接
   - 或设置访问密码

### 数据安全

- ✅ 使用HTTPS加密传输
- ✅ 不存储用户敏感信息
- ⚠️ 历史记录保存在本地浏览器
- ⚠️ 不要在公共电脑上使用

---

## 🐛 常见问题

### 1. 页面无法加载

**问题**: 访问网站显示404

**解决**:
- 检查GitHub Pages是否已启用
- 等待1-2分钟让部署完成
- 确认仓库名称正确

### 2. API调用失败

**问题**: 提示API密钥无效

**解决**:
- 检查config.js中的API密钥是否正确
- 确认API密钥未过期
- 检查是否设置了使用限额

### 3. 股票数据无法显示

**问题**: 无法获取实时股价

**解决**:
- Yahoo Finance API可能不稳定，稍后重试
- 检查股票代码是否正确
- 某些股票可能不被支持

### 4. 图表无法显示

**问题**: 点击图表按钮没有反应

**解决**:
- 检查Chart.js是否正确加载
- 打开浏览器控制台查看错误
- 刷新页面重试

---

## 🔄 更新日志

### v1.0.0 (2026-01-31)

- ✅ 初始版本发布
- ✅ ChatGPT风格对话界面
- ✅ 支持A股、美股、黄金分析
- ✅ K线图、分时图、组合图
- ✅ 27项投资分析能力
- ✅ 响应式设计
- ✅ 深色/浅色主题

---

## 📚 参考资源

### 官方文档

- [Claude API文档](https://docs.anthropic.com/)
- [Chart.js文档](https://www.chartjs.org/)
- [GitHub Pages文档](https://docs.github.com/en/pages)

### 相关项目

- [投资分析预测技能](https://github.com/) - Claude Code技能版本

---

## 📄 许可证

MIT License

Copyright (c) 2026 AI Investment Assistant

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## ⚠️ 免责声明

所有分析仅供参考，不构成投资建议。

**风险提示**:
- 股市有风险，投资需谨慎
- 过往表现不代表未来收益
- 所有预测都存在不确定性
- 请根据自身情况做出决策
- 建议咨询专业投资顾问

---

**Made with ❤️ by Claude AI**

**最后更新**: 2026-01-31
