# Unsplash API 动态备选图片配置指南

## 功能说明

现在系统支持从 Unsplash API 动态获取与诗词主题相关的备选图片，当 AI 图片生成失败时，会自动获取最匹配的图片作为备选。

## 配置步骤

### 1. 获取 Unsplash API Key

1. 访问 [Unsplash Developers](https://unsplash.com/developers)
2. 注册/登录账户
3. 创建新应用
4. 获取 Access Key

### 2. 设置环境变量

将获取的 Access Key 设置为环境变量：

```bash
export UNSPLASH_ACCESS_KEY="your_access_key_here"
```

或者在代码中直接设置：
```python
UNSPLASH_ACCESS_KEY = "your_access_key_here"
```

## 工作原理

### 智能主题匹配

系统会根据诗词内容智能分析主题，并选择相应的关键词：

- **自然主题** (nature): landscape, mountain, forest, river, lake, sky
- **季节主题** (season): spring, summer, autumn, winter, bloom, snow
- **情感主题** (emotion): peaceful, serene, calm, tranquil, meditation, zen
- **默认主题** (default): beautiful, scenic, artistic, poetic, landscape

### 中文元素映射

系统会将诗词中的中文元素转换为英文关键词：
- 山 → mountain
- 水 → water  
- 树 → tree
- 花 → flower
- 云 → cloud
- 月 → moon
- 等等...

### 备选策略

1. **优先使用 Unsplash API** - 根据诗词主题动态获取相关图片
2. **静态备选图片** - 当 API 失败时使用预设的高质量图片
3. **智能降级** - 确保系统始终有图片可用

## 使用示例

```python
# 系统会自动：
# 1. 分析诗词主题
# 2. 选择合适的关键词
# 3. 从 Unsplash 搜索相关图片
# 4. 随机选择一张高质量图片
# 5. 如果失败，使用静态备选图片

sentence = "春眠不觉晓，处处闻啼鸟"
# 系统会分析为"nature"主题，搜索"spring", "bird", "nature"等关键词
```

## 注意事项

- Unsplash API 有使用限制，请合理使用
- 建议设置环境变量而不是硬编码 API Key
- 系统会自动处理 API 失败的情况
- 所有操作都有详细的日志记录

## 日志示例

```
INFO: Analyzing poetry theme: nature
INFO: Searching Unsplash for keyword: spring
INFO: Successfully fetched Unsplash image: https://images.unsplash.com/photo-xxx
INFO: Using fallback image for GitHub comment
```
