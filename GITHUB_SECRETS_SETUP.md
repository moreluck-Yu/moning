# GitHub Secrets 配置指南

## 📋 **配置步骤**

### 1. **进入 GitHub 仓库设置**

1. 打开您的 GitHub 仓库页面
2. 点击 **Settings** 标签页
3. 在左侧菜单中找到 **Secrets and variables** → **Actions**
4. 点击 **New repository secret** 按钮

### 2. **添加必需的 Secrets**

#### **OPENROUTER_API_KEY** (必需)
- **Name**: `OPENROUTER_API_KEY`
- **Value**: 您的 OpenRouter API Key
- **获取方式**: 
  1. 访问 [OpenRouter](https://openrouter.ai/)
  2. 注册/登录账户
  3. 在 Dashboard 中创建 API Key
  4. 复制生成的 API Key

#### **UNSPLASH_ACCESS_KEY** (可选，用于备选图片)
- **Name**: `UNSPLASH_ACCESS_KEY`
- **Value**: 您的 Unsplash Access Key
- **获取方式**:
  1. 访问 [Unsplash Developers](https://unsplash.com/developers)
  2. 注册/登录账户
  3. 创建新应用
  4. 获取 Access Key

### 3. **现有的 Secrets (保持不变)**

这些 Secrets 应该已经存在，请保持原样：
- `OPENAI_API_KEY` - 用于诗词分析
- `OPENAI_API_BASE` - OpenAI API 基础 URL
- `G_T` - GitHub Token
- `TG_TOKEN` - Telegram Bot Token
- `TG_CHAT_ID` - Telegram Chat ID

### 4. **移除不再需要的 Secrets**

可以删除以下 Secret（如果存在）：
- `KLING_COOKIE` - 不再需要

## 🔧 **GitHub Actions 配置更新**

您的 `.github/workflows/get_up.yml` 文件已经更新为：

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
  UNSPLASH_ACCESS_KEY: ${{ secrets.UNSPLASH_ACCESS_KEY }}
  OPENAI_API_BASE: ${{ secrets.OPENAI_API_BASE }}
```

## 📊 **完整的 Secrets 列表**

### 必需 Secrets:
```
OPENROUTER_API_KEY = sk-or-v1-xxx
OPENAI_API_KEY = sk-xxx
G_T = ghp_xxx
```

### 可选 Secrets:
```
UNSPLASH_ACCESS_KEY = xxx
OPENAI_API_BASE = https://api.openai.com/v1
TG_TOKEN = xxx
TG_CHAT_ID = xxx
```

## 🚀 **测试配置**

### 1. **手动触发测试**
1. 进入 GitHub 仓库的 **Actions** 标签页
2. 选择 **GET UP** workflow
3. 点击 **Run workflow** 按钮
4. 查看运行日志确认配置正确

### 2. **检查日志**
在 Actions 日志中查找以下信息：
- ✅ `OPENROUTER_API_KEY configured` - API Key 配置成功
- ✅ `Generating image with Gemini` - 开始生成图片
- ✅ `Successfully generated image` - 图片生成成功
- ✅ `Using AI generated image` - 使用 AI 生成图片

### 3. **常见错误**
- ❌ `OPENROUTER_API_KEY not configured` - 检查 Secret 是否添加
- ❌ `Failed to generate image with Gemini` - 检查 API Key 是否有效
- ❌ `Using fallback image` - 图片生成失败，使用备选图片

## 📅 **定时运行**

您的 workflow 配置为每天凌晨 1 点运行：
```yaml
schedule:
  - cron: "0 01 * * *"
```

## 🔍 **故障排除**

### 1. **API Key 无效**
- 检查 OpenRouter API Key 是否正确
- 确认账户有足够的免费额度

### 2. **网络问题**
- GitHub Actions 运行在云端，通常网络连接正常
- 如果持续失败，可能是 OpenRouter 服务问题

### 3. **权限问题**
- 确认 GitHub Token 有足够的权限
- 检查仓库的 Actions 权限设置

## 📝 **更新记录**

- ✅ 移除了 `KLING_COOKIE` 依赖
- ✅ 添加了 `OPENROUTER_API_KEY` 配置
- ✅ 添加了 `UNSPLASH_ACCESS_KEY` 配置
- ✅ 更新了 git add 命令（移除了 questions.txt）

## 🎯 **下一步**

1. 按照上述步骤配置 GitHub Secrets
2. 手动触发一次 workflow 测试
3. 检查生成的图片和日志
4. 确认每天自动运行正常

配置完成后，您的早起记录系统将使用更稳定、更高质量的 Gemini 图片生成服务！
