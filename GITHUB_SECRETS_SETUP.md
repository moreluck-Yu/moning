# GitHub Secrets 配置指南

## 📋 配置步骤

### 1. 进入 GitHub 仓库设置
1. 打开仓库页面
2. 点击 **Settings**
3. 左侧选择 **Secrets and variables** → **Actions**
4. 点击 **New repository secret**

### 2. 添加必需的 Secrets

#### **GEMINI_IMAGEN_API_KEY** (必需)
- **Name**: `GEMINI_IMAGEN_API_KEY`
- **Value**: Gemini Imagen 的 API Key

#### **GITHUB_TOKEN** (必需)
- **Name**: `GITHUB_TOKEN`
- **Value**: 具备 Issues 写权限的 GitHub Token

#### **GITHUB_REPO** (必需)
- **Name**: `GITHUB_REPO`
- **Value**: 仓库名（格式: `owner/repo`）

### 3. 可选 Secrets

#### **UNSPLASH_ACCESS_KEY** (可选)
- **Name**: `UNSPLASH_ACCESS_KEY`
- **Value**: Unsplash Access Key

#### **TG_TOKEN** / **TG_CHAT_ID** (可选)
- **Name**: `TG_TOKEN`
- **Value**: Telegram Bot Token
- **Name**: `TG_CHAT_ID`
- **Value**: Telegram Chat ID

### 4. 可选环境变量（可放在 workflow 中）
这些不一定需要存为 Secret，代码内已有默认值，仅在需要覆盖时设置：
- `GEMINI_IMAGEN_API_BASE`（自定义 API Base 时使用）
- `GEMINI_IMAGEN_MODEL`（默认 `nano-banana`）
- `FENXI_MODEL`（默认 `grok-4.1-thinking`）
- `GEMINI_IMAGEN_TIMEOUT`
- `UNSPLASH_TIMEOUT`
- `OUTPUT_DIR`

## 🔧 GitHub Actions 配置示例

如果你使用 GitHub Actions，可在 workflow 中配置如下环境变量：

```yaml
env:
  GEMINI_IMAGEN_API_KEY: ${{ secrets.GEMINI_IMAGEN_API_KEY }}
  UNSPLASH_ACCESS_KEY: ${{ secrets.UNSPLASH_ACCESS_KEY }}
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  GITHUB_REPO: ${{ secrets.GITHUB_REPO }}
  TG_TOKEN: ${{ secrets.TG_TOKEN }}
  TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
```

## 🚀 测试配置

本地测试：
```bash
python moning_main.py --config-check
python moning_main.py --dry-run
```

## 🔍 常见问题

### 1. 配置错误
- 运行 `python moning_main.py --config-check` 查看缺失项

### 2. 发布失败
- 检查 `GITHUB_TOKEN` 是否有 Issues 写权限
- 确认 `GITHUB_REPO` 格式为 `owner/repo`

### 3. 图片生成失败
- 检查 `GEMINI_IMAGEN_API_KEY` 是否有效
- 若使用自定义 API Base，确认 `GEMINI_IMAGEN_API_BASE` 正确

---

配置完成后即可运行日常打卡流程。
