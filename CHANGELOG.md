# 🔄 更新说明 - 已切换到智谱AI

## 更新时间: 2026-01-31

---

## ✅ 已完成的更改

### 1. API提供商切换

✨ **从 Claude API 切换到 智谱AI API**

**原因**:
- 用户提供了智谱AI的API密钥
- 智谱AI是中国领先的AI模型提供商
- GLM-4模型在中文投资分析方面表现优秀

### 2. 修改的文件

#### config.js
- ❌ 删除: `CLAUDE_API_KEY`, `CLAUDE_MODEL`, `CLAUDE_API_ENDPOINT`
- ✅ 添加: `ZHIPU_API_KEY`, `ZHIPU_MODEL`, `ZHIPU_API_ENDPOINT`
- 📝 已配置您的API密钥: `6c17c076f2934c50a09a21dae5195c33.RfWC2RgrZN0IpfOE`

#### js/api.js
- 修改: `callClaudeAPI()` 函数实现
- 新的API端点: `https://open.bigmodel.cn/api/paas/v4/chat/completions`
- 请求格式改为OpenAI兼容格式
- 响应解析适配智谱AI的返回格式

#### js/api.js - handleAPIError()
- 更新错误提示信息
- 添加智谱AI特有的错误类型识别（余额不足、频率限制等）

#### README.md
- 更新API密钥获取说明
- 更新配置说明
- 更新技术栈说明
- 更新成本分析

#### DEPLOYMENT_GUIDE.md
- 全局替换 "Claude" → "智谱AI"
- 全局替换 "Anthropic" → "智谱AI / Zhipu AI"

---

## 🚀 智谱AI API 信息

### API端点
```
https://open.bigmodel.cn/api/paas/v4/chat/completions
```

### 支持的模型

| 模型 | 说明 | 价格 | 推荐用途 |
|:---|:---|:---:|:---|
| **glm-4-plus** | 最强大的模型 | ¥0.05/千tokens | 复杂分析、深度研究 |
| **glm-4-flash** | 快速响应 | ¥0.001/千tokens | 日常查询、快速回答 |

### 免费额度
- 新用户注册后通常有免费额度
- 具体额度请查看智谱AI控制台

---

## 💡 使用建议

### 模型选择

**推荐配置 (默认)**:
```javascript
ZHIPU_MODEL: 'glm-4-plus'  // 质量优先
```

**节省成本配置**:
```javascript
ZHIPU_MODEL: 'glm-4-flash'  // 速度优先，成本更低
```

### 成本对比

**GLM-4-Plus** (默认):
- 输入: ¥0.05/千tokens
- 输出: ¥0.05/千tokens
- 日常使用: 约¥5-50/月

**GLM-4-Flash** (推荐):
- 输入: ¥0.001/千tokens
- 输出: ¥0.001/千tokens
- 日常使用: 约¥0.1-1元/月 (非常便宜！)

---

## ⚠️ 重要提示

### API密钥安全

您的API密钥已配置在 `config.js` 中：
```
6c17c076f2934c50a09a21dae5195c33.RfWC2RgrZN0IpfOE
```

**安全建议**:
1. ✅ 仅限个人使用
2. ✅ 不要公开分享网站链接
3. ✅ 定期检查使用情况
4. ✅ 设置每日/每月消费限额
5. ❌ 不要将包含API密钥的文件上传到公开仓库

### 如何设置限额？

1. 访问智谱AI控制台: https://open.bigmodel.cn/
2. 登录您的账号
3. 找到"API管理"或"费用中心"
4. 设置每日或每月消费限额
5. 开启超额提醒

---

## 🔧 如果要切换模型

### 切换到 GLM-4-Flash (更便宜)

打开 `config.js`，修改:

```javascript
// 修改前
ZHIPU_MODEL: 'glm-4-plus',

// 修改后
ZHIPU_MODEL: 'glm-4-flash',
```

保存文件并重新上传到GitHub即可。

---

## 📊 性能对比

### Claude API vs 智谱AI

| 特性 | Claude API | 智谱AI |
|:---|:---:|:---:|
| 中文理解 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 投资分析 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 响应速度 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 成本 | 较高 | 低 |
| 国内访问 | 可能较慢 | 快速 |

### 推荐理由

智谱AI的优势：
- ✅ 专为中文优化
- ✅ 在金融投资领域表现优秀
- ✅ 价格更实惠
- ✅ 国内访问速度快
- ✅ 符合国内数据合规要求

---

## 🎯 下一步操作

### 立即可用

您的系统已配置完成，可以直接使用！

1. **测试API连接**
   - 上传文件到GitHub Pages
   - 访问网站
   - 输入: "你好"
   - 查看是否能正常回复

2. **测试股票分析**
   - 输入: "分析一下贵州茅台"
   - 查看是否能正常分析

3. **测试图表功能**
   - 点击图表按钮
   - 查看K线图是否正常显示

---

## 📞 获取帮助

### 智谱AI官方资源

- **官网**: https://open.bigmodel.cn/
- **文档**: https://open.bigmodel.cn/dev/api
- **控制台**: https://open.bigmodel.cn/usercenter/apikeys

### 常见问题

**Q: API余额不足怎么办？**
A: 登录智谱AI控制台充值

**Q: 如何查看使用情况？**
A: 在控制台的"使用记录"中查看

**Q: API调用失败？**
A: 检查网络连接、API密钥是否正确、余额是否充足

---

## ✅ 更新清单

- [x] config.js - 切换到智谱AI
- [x] js/api.js - 修改API调用实现
- [x] README.md - 更新文档
- [x] DEPLOYMENT_GUIDE.md - 更新部署指南
- [x] 配置用户提供的API密钥

---

**祝您使用愉快！** 🎉

如有问题，请查看智谱AI官方文档或联系技术支持。

**更新时间**: 2026-01-31
**版本**: v2.0.0 - 智谱AI版
