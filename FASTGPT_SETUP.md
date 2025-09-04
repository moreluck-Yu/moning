# FastGPT FLUX.1 DEV 图片生成配置指南

## 功能说明

系统已从 OpenRouter + Gemini 迁移到使用 FastGPT API + FLUX.1 DEV 模型的图片生成方案。这个方案直接生成AI图片，更加稳定、高效，并且能够根据诗词内容生成高质量的AI图片。

## 工作原理

### 🔄 **新的图片生成流程**

```
诗词分析 → 增强提示词 → FastGPT FLUX.1 DEV → 直接生成AI图片
```

### 🧠 **AI图片生成机制**

1. **诗词分析**: 分析诗词主题和意境
2. **提示词增强**: 根据诗词内容生成专业的图片描述
3. **AI图片生成**: 使用FLUX.1 DEV模型直接生成AI图片
4. **高质量输出**: 返回1024x1024的高质量AI图片

## 配置步骤

### 1. **GitHub Secrets 配置**

进入您的 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

#### **必需的 Secrets：**
```
Name: FASTGPT_API_KEY
Value: fastgpt-xwRC0Ea1FFFFGR0xJZjhz0zTyGXuwJdbzhDt31igWvyYsLkWf1qZzhjXICt5
```

#### **可选的 Secrets：**
```
Name: UNSPLASH_ACCESS_KEY
Value: your_unsplash_access_key_here
```

### 2. **API 配置详情**

#### **FastGPT API**
- **请求地址**: `https://api.fastgpt.in/api/v1/chat/completions`
- **模型**: `FLUX.1 DEV`
- **用途**: 直接生成AI图片
- **认证**: API Key 认证
- **图片尺寸**: 1024x1024
- **图片质量**: Standard

## 技术优势

### 📊 **方案对比**

| 特性 | OpenRouter + Gemini | FastGPT + FLUX.1 DEV |
|------|-------------------|---------------------|
| **稳定性** | 依赖第三方服务 | 更稳定可靠 |
| **成本** | 可能产生费用 | 更经济实惠 |
| **图片质量** | AI生成，质量不定 | FLUX.1 DEV高质量生成 |
| **相关性** | 基于提示词生成 | 智能提示词增强 |
| **多样性** | 每次生成不同 | 每次生成独特图片 |

### 🎯 **核心优势**

1. **直接生成**: FLUX.1 DEV模型直接生成AI图片，无需搜索
2. **高质量输出**: FLUX.1 DEV提供高质量的AI图片生成
3. **智能理解**: 根据诗词内容智能生成相关图片
4. **稳定可靠**: 基于FastGPT的稳定API服务
5. **独特创意**: 每次生成都是独特的AI艺术作品

## 工作流程详解

### 1. **诗词分析阶段**
```python
# 分析诗词主题
theme, analysis = analyze_poetry_theme(sentence)
# 生成增强提示词
enhanced_prompt = generate_enhanced_prompt(sentence)
```

### 2. **AI图片生成阶段**
```python
# FastGPT FLUX.1 DEV生成AI图片
image_prompt = f"""
Generate a beautiful, artistic image based on this Chinese poetry description: {enhanced_prompt}

The image should be:
- High quality and visually appealing
- Suitable for a morning poetry sharing context
- Artistic and inspiring
- In landscape orientation
- Reflect the mood and theme of the poetry
"""

response = fastgpt_client.images.generate(
    model=FASTGPT_MODEL,
    prompt=image_prompt,
    size="1024x1024",
    quality="standard",
    n=1
)
```

### 3. **图片获取阶段**
```python
# 获取生成的AI图片URL
if response.data and len(response.data) > 0:
    image_url = response.data[0].url
    return image_url
```

## 错误处理机制

### 🔄 **多层备选策略**

```
FastGPT FLUX.1 DEV → Unsplash搜索 → 静态备选图片 → 无图片提示
```

### 🛡️ **重试机制**

- **重试次数**: 最多3次
- **重试间隔**: 指数退避 (2秒, 4秒, 8秒)
- **超时设置**: 10秒超时保护

### 📝 **详细日志**

系统会记录：
- FastGPT FLUX.1 DEV图片生成过程
- API请求和响应状态
- 图片生成结果
- 错误信息和重试过程

## 使用示例

### **诗词示例**
```
输入诗词: "春眠不觉晓，处处闻啼鸟"
增强提示词: "Create a beautiful landscape with spring morning, birds singing..."
FLUX.1 DEV生成: 直接生成AI图片
返回图片: 独特的春天早晨AI艺术作品
```

### **消息显示**
```
#Now 记录时间是--2024-09-03 08:30:00.

今天的一句诗:
春眠不觉晓，处处闻啼鸟

📅 年度进度:
█████████████░░░░░░░ 67.7% (247/365)

![image](https://generated-images.fastgpt.com/xxx)

*AI生成图片*
```

## 配置检查

### ✅ **必需配置**
- `FASTGPT_API_KEY` - FastGPT API密钥
- `UNSPLASH_ACCESS_KEY` - Unsplash访问密钥（备选方案，可选）

### ✅ **现有配置保持不变**
- `OPENAI_API_KEY` - 用于诗词分析
- `G_T` - GitHub Token
- `TG_TOKEN` - Telegram Bot Token
- `TG_CHAT_ID` - Telegram Chat ID

## 故障排除

### 常见问题

1. **FastGPT API 调用失败**
   - 检查 `FASTGPT_API_KEY` 是否正确配置
   - 确认网络连接正常

2. **FLUX.1 DEV 图片生成失败**
   - 检查API密钥是否有效
   - 系统会自动使用Unsplash备选图片

3. **图片生成质量不佳**
   - FLUX.1 DEV会根据提示词智能生成
   - 重试机制会尝试重新生成

### 日志示例

```
INFO: Generating image with FastGPT FLUX.1 DEV for prompt: Create a beautiful landscape...
INFO: Successfully generated image with FastGPT: https://generated-images.fastgpt.com/xxx
INFO: Using AI generated image for GitHub comment
```

## 迁移完成

✅ **已移除**: OpenRouter + Gemini 相关代码  
✅ **已添加**: FastGPT + FLUX.1 DEV 集成  
✅ **已实现**: 直接AI图片生成功能  
✅ **已更新**: GitHub Actions 配置  
✅ **已测试**: 新的图片生成流程  

现在您的早起记录系统使用更稳定、更高效的AI图片生成方案！
