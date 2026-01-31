# 🚀 AI投资分析助手 - 零基础部署指南

> 专为非技术人员设计，5分钟完成网站部署

---

## 📋 准备工作检查清单

在开始之前，请确保您已准备好：

- [ ] 一台可以上网的电脑 (Windows/Mac都可以)
- [ ] 一个现代浏览器 (Chrome、Edge、Firefox等)
- [ ] 智谱AI API密钥 (已获取✅)

---

## 第一步: 注册GitHub账号 (如果还没有)

### 什么是GitHub？
GitHub是全球最大的代码托管平台，提供免费的网页托管服务(GitHub Pages)。

### 如何注册？

1. **打开GitHub官网**
   - 访问: https://github.com/
   - 点击右上角的 "Sign up"

2. **填写注册信息**
   - 用户名: 建议使用英文或数字 (例如: zhangsan1988)
   - 邮箱: 您常用的邮箱
   - 密码: 设置一个安全密码

3. **验证账号**
   - GitHub会发送验证邮件到您的邮箱
   - 点击邮件中的验证链接
   - 完成验证

4. **创建个人信息** (可选)
   - 可以选择跳过
   - 以后可以随时补充

⏱️ **预计时间**: 3-5分钟

---

## 第二步: 配置项目文件

### 2.1 下载项目文件

您应该已经拥有以下文件:

```
investment-web/
├── index.html
├── config.js
├── README.md
├── css/
│   └── style.css
└── js/
    ├── app.js
    ├── api.js
    ├── chart.js
    └── utils.js
```

### 2.2 配置API密钥

这是**最重要的一步**！

1. **打开config.js文件**

   用记事本或任何文本编辑器打开 `config.js` 文件

2. **找到API配置部分**

   在文件开头找到:
   ```javascript
   const CONFIG = {
       CLAUDE_API_KEY: 'YOUR_CLAUDE_API_KEY_HERE',
   ```

3. **替换API密钥**

   将 `YOUR_CLAUDE_API_KEY_HERE` 替换为您的实际密钥

   **示例**:
   ```javascript
   // 修改前
   CLAUDE_API_KEY: 'YOUR_CLAUDE_API_KEY_HERE',

   // 修改后 (假设您的密钥是 sk-ant-abc123...)
   CLAUDE_API_KEY: 'sk-ant-abc123xyz...',
   ```

4. **保存文件**

   - 文件 → 保存 (或 Ctrl+S)

⚠️ **重要提示**:
- 不要把API密钥告诉他人
- 不要把包含API密钥的文件公开分享
- 建议在智谱AI / Zhipu AI控制台设置每月限额

⏱️ **预计时间**: 2分钟

---

## 第三步: 上传到GitHub (方式一: 网页上传 - 推荐)

这是**最简单**的方式，不需要安装任何软件。

### 3.1 创建新仓库

1. **登录GitHub**
   - 访问: https://github.com/
   - 点击右上角 "Sign in" 登录

2. **创建新仓库**
   - 点击右上角 "+" 图标
   - 选择 "New repository"

3. **填写仓库信息**
   - Repository name: `investment-web` (必须用这个名字)
   - Description: `AI投资分析助手` (可选)
   - 选择 **Public** (公开) - 这是免费的
   - ❌ **不要**勾选 "Add a README file"
   - ❌ **不要**勾选其他选项

4. **点击 "Create repository"**

### 3.2 上传文件

1. **进入上传页面**
   - 创建仓库后会跳转
   - 点击 "uploading an existing file"

2. **拖拽文件上传**

   方法一: 拖拽整个文件夹
   - 直接将 `investment-web` 文件夹拖到上传区域

   方法二: 逐个选择文件
   - 点击 "choose your files"
   - 选择所有文件 (Ctrl+A全选)

3. **确认文件列表**

   上传后应该看到:
   ```
   css/
     style.css
   js/
     app.js
     api.js
     chart.js
     utils.js
   index.html
   config.js
   README.md
   ```

4. **提交文件**
   - 在 "Commit changes" 框中输入: "Initial commit"
   - 点击绿色按钮 "Commit changes"

⏱️ **预计时间**: 5-8分钟

---

## 第四步: 启用GitHub Pages

### 什么是GitHub Pages？
GitHub Pages是GitHub提供的免费网页托管服务，可以托管静态网站。

### 如何启用？

1. **进入仓库设置**
   - 在仓库页面顶部点击 "Settings" (设置图标⚙️)

2. **找到Pages设置**
   - 左侧菜单中找到 "Pages" (在"Code and automation"部分)
   - 点击进入

3. **配置部署来源**

   在 "Build and deployment" 部分:
   - Source: 选择 "Deploy from a branch"
   - Branch: 选择 "main"
   - Folder: 选择 "/root" (根目录)

4. **保存设置**
   - 点击 "Save" (保存)

5. **等待部署**

   页面会显示:
   - Your site is live at: https://YOUR_USERNAME.github.io/investment-web/
   - ⏱️ 等待1-2分钟让部署完成

⏱️ **预计时间**: 2分钟

---

## 第五步: 访问您的网站

### 5.1 获取网址

在Pages设置页面会显示您的网站地址:

```
https://YOUR_USERNAME.github.io/investment-web/
```

将 `YOUR_USERNAME` 替换为您的GitHub用户名。

**示例**:
- 如果您的用户名是 `zhangsan1988`
- 网址就是: `https://zhangsan1988.github.io/investment-web/`

### 5.2 访问网站

1. **复制网址**
   - 点击网址旁边的复制按钮

2. **打开浏览器**
   - 新建标签页
   - 粘贴网址并回车

3. **测试功能**
   - 尝试输入: "你好"
   - 应该能看到AI的回复

### 5.3 收藏网址

- Ctrl+D (Windows) 或 Cmd+D (Mac) 收藏网址
- 方便以后快速访问

⏱️ **预计时间**: 1分钟

---

## 🎉 恭喜！您已完成部署

您的AI投资分析助手现在已经上线了！

### 您可以做什么？

✅ **随时访问**
- 在任何设备上访问网址
- 手机、平板、电脑都可以

✅ **提问咨询**
- 股票分析
- 黄金价格
- 市场事件
- 投资建议

✅ **查看图表**
- K线图
- 分时图
- 组合图

---

## 🔧 常见问题解决

### 问题1: 网站显示404

**原因**: GitHub Pages还在部署中

**解决**:
- 等待1-2分钟
- 刷新页面 (F5)
- 清除浏览器缓存

### 问题2: 提示API密钥错误

**原因**: config.js中的API密钥未配置或配置错误

**解决**:
1. 重新编辑config.js
2. 确认API密钥完全正确
3. 保存后重新上传文件

### 问题3: 无法获取股票数据

**原因**: Yahoo Finance API可能不稳定

**解决**:
- 等待几分钟后重试
- 或配置Alpha Vantage API (可选)

### 问题4: 如何更新网站？

**解决**:
1. 修改本地文件
2. 访问仓库页面
3. 点击 "Add file" → "Upload files"
4. 上传修改后的文件
5. 点击 "Commit changes"
6. 等待1-2分钟自动部署

---

## 💡 使用技巧

### 技巧1: 添加到手机主屏幕

**iPhone/iPad**:
1. 用Safari打开网站
2. 点击分享按钮
3. 选择"添加到主屏幕"

**Android**:
1. 用Chrome打开网站
2. 点击菜单 (三个点)
3. 选择"添加到主屏幕"

### 技巧2: 创建桌面快捷方式

**Windows**:
1. 在桌面右键 → 新建 → 快捷方式
2. 输入网址
3. 命名为"AI投资助手"

**Mac**:
1. 打开Safari
2. 将网址图标拖到桌面

### 技巧3: 设置API使用限额

为了避免意外费用，建议设置限额:

1. 访问: https://console.anthropic.com/
2. 登录账号
3. 找到 "Usage" 或 "Billing"
4. 设置每月限额 (例如: $20)

---

## 📊 成本说明

### 完全免费的部分

- GitHub托管: ¥0/月
- 网站访问: ¥0 (无限流量)
- 域名: ¥0/年
- Yahoo Finance API: ¥0/月

### 需要付费的部分

- **智谱AI API**: 按使用量付费
  - 新用户有免费额度
  - 日常使用: 约¥5-50/月
  - 可以设置每月限额控制费用

### 节省成本的建议

1. 设置API使用限额
2. 避免频繁重复提问
3. 定期检查使用情况
4. 不使用时可以暂时下线网站

---

## 🔐 安全建议

### 保护您的API密钥

⚠️ **重要**: 由于是纯前端网站，API密钥在网页代码中是可见的。

**建议**:
1. ✅ 仅限个人使用，不要公开分享网址
2. ✅ 设置每月使用限额
3. ✅ 定期更换API密钥 (每月一次)
4. ✅ 监控API使用情况
5. ❌ 不要在公开场合分享链接

### 如果担心安全问题

如果您担心API密钥泄露，可以考虑:

**选项1: 使用临时密钥**
- 定期生成新的API密钥
- 旧密钥立即作废

**选项2: 设置IP限制** (如果智谱AI / Zhipu AI支持)
- 限制API只能从特定IP调用

**选项3: 使用后端服务** (高级)
- 需要一定技术能力
- 可以完全隐藏API密钥
- 需要额外的服务器费用

---

## 📚 下一步学习

### 推荐阅读

1. **README.md** - 完整功能说明
2. **config.js** - 了解可配置选项
3. **投资知识** - 学习27项投资分析能力

### 进阶使用

1. **自定义提示词**
   - 修改config.js中的SYSTEM_PROMPT
   - 添加您偏好的分析风格

2. **添加更多股票代码**
   - 在config.js的STOCK_SYMBOLS中添加
   - 支持更多股票和指数

3. **修改界面样式**
   - 编辑css/style.css
   - 自定义颜色和布局

---

## 🆘 获取帮助

### 遇到问题？

1. **查看README.md**
   - 包含完整的功能说明和FAQ

2. **检查浏览器控制台**
   - 按F12打开开发者工具
   - 查看Console标签页的错误信息

3. **重新部署**
   - 有时重新上传文件可以解决问题

### 联系支持

如果您遇到严重问题:
- 检查GitHub仓库的Issues页面
- 查看是否有其他人遇到类似问题
- 提交新的Issue描述您的问题

---

## ✅ 部署完成检查清单

部署完成后，请检查以下项目:

- [ ] 网站可以正常访问
- [ ] 可以正常输入问题
- [ ] AI能够正常回复
- [ ] 股票数据显示正常
- [ ] 图表可以正常查看
- [ ] 手机上可以正常访问
- [ ] 已设置API使用限额
- [ ] 已收藏网址方便下次访问

全部打勾？恭喜您成功部署！🎉

---

## 📝 快速参考卡

### 网站访问地址

```
https://YOUR_USERNAME.github.io/investment-web/
```

### GitHub仓库地址

```
https://github.com/YOUR_USERNAME/investment-web
```

### 智谱AI API控制台

```
https://console.anthropic.com/
```

### 文件位置

- 配置文件: `/config.js`
- 主页面: `/index.html`
- 使用说明: `/README.md`

---

**祝您使用愉快！** 💼📈

**最后更新**: 2026-01-31
**版本**: 1.0.0
