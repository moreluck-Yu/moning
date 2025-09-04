# OpenRouter + Gemini 图片生成配置指南

## 功能说明

系统已从 Kling AI 迁移到使用 OpenRouter API 调用 Google Gemini 2.0 Flash Exp 模型进行图片生成。这个方案更加稳定、快速，并且支持更好的图片质量。

## 配置步骤

### 1. 获取 OpenRouter API Key

1. 访问 [OpenRouter](https://openrouter.ai/)
2. 注册/登录账户
3. 在 Dashboard 中创建 API Key
4. 复制生成的 API Key

### 2. 设置环境变量

将获取的 API Key 设置为环境变量：

```bash
export OPENROUTER_API_KEY="your_openrouter_api_key_here"
```

或者在代码中直接设置：
```python
OPENROUTER_API_KEY = "your_openrouter_api_key_here"
```

## 技术细节

### 使用的模型
- **模型名称**: `google/gemini-2.0-flash-exp:free`
- **模型类型**: Google Gemini 2.0 Flash Experimental (免费版)
- **图片尺寸**: 1024x1024
- **图片质量**: Standard

### API 配置
```python
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
GEMINI_MODEL = "google/gemini-2.0-flash-exp:free"
```

### 图片生成流程

1. **诗词分析** → 识别主题和元素
2. **提示词增强** → 生成专业的图片描述
3. **Gemini 调用** → 通过 OpenRouter API 生成图片
4. **重试机制** → 最多3次重试，指数退避
5. **备选方案** → 失败时使用 Unsplash 备选图片

## 优势对比

### 相比 Kling AI 的优势

| 特性 | Kling AI | OpenRouter + Gemini |
|------|----------|-------------------|
| 稳定性 | 依赖 Cookie | API Key 认证 |
| 速度 | 较慢 | 更快 |
| 质量 | 一般 | 高质量 |
| 维护 | 需要更新 Cookie | 无需维护 |
| 成本 | 免费但有限制 | 免费额度充足 |

### 图片生成特点

- **高质量**: Gemini 2.0 提供更高质量的图片生成
- **快速响应**: 通常几秒内完成生成
- **稳定可靠**: 基于 API 的稳定服务
- **智能理解**: 更好地理解中文诗词意境

## 错误处理

### 自动降级策略

```
Gemini 图片生成失败 → Unsplash 动态获取 → 静态备选图片
```

### 重试机制

- **重试次数**: 最多3次
- **重试间隔**: 指数退避 (2秒, 4秒, 8秒)
- **超时设置**: 60秒超时保护

### 日志记录

系统会详细记录：
- 图片生成请求
- API 响应状态
- 错误信息和重试过程
- 最终使用的图片类型

## 使用示例

### 环境变量设置
```bash
# 必需的环境变量
export OPENROUTER_API_KEY="sk-or-v1-xxx"
export OPENAI_API_KEY="sk-xxx"  # 用于诗词分析
export OPENAI_API_BASE="https://api.openai.com/v1"  # 可选

# 可选的环境变量
export UNSPLASH_ACCESS_KEY="xxx"  # 用于备选图片
```

### 运行脚本
```bash
python get_up.py <github_token> <repo_name> [--weather_message] [--tele_token] [--tele_chat_id]
```

## 注意事项

1. **API 限制**: OpenRouter 有使用限制，但免费额度通常足够日常使用
2. **网络要求**: 需要能够访问 openrouter.ai
3. **图片格式**: 生成的图片为 PNG 格式，1024x1024 分辨率
4. **存储**: 图片 URL 直接使用，无需本地存储

## 故障排除

### 常见问题

1. **API Key 无效**
   - 检查环境变量是否正确设置
   - 确认 API Key 是否有效

2. **网络连接问题**
   - 检查网络连接
   - 确认防火墙设置

3. **图片生成失败**
   - 查看日志了解具体错误
   - 系统会自动使用备选图片

### 日志示例

```
INFO: Generating image with Gemini for prompt: Create a beautiful, serene landscape...
INFO: Successfully generated image: https://generated-images.google.com/xxx
INFO: Using AI generated image for GitHub comment
```

## 迁移完成

✅ **已移除**: Kling AI 相关代码和依赖  
✅ **已添加**: OpenRouter API 集成  
✅ **已实现**: Gemini 图片生成功能  
✅ **已更新**: 错误处理和重试机制  
✅ **已测试**: 新的图片生成流程  

现在您的早起记录系统使用更稳定、更高质量的图片生成服务！
