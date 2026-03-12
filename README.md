# Moning 项目索引

## 项目概述

Moning 是一个智能化的个人习惯养成系统，通过 AI 驱动的多模态内容生成与多平台分发，构建可持续的早起打卡仪式感。当前代码库聚焦早起打卡链路，旧版文档中提到的单词学习模块属于历史/规划内容。

## 核心文档索引

### 📋 项目管理文档
- **[README.md](README.md)** - 项目介绍和快速开始指南
- **[LICENSE](LICENSE)** - 项目许可证
- **[requirements.txt](requirements.txt)** - Python 依赖清单

### 🏗️ 架构与设计文档
- **[DESIGN.md](DESIGN.md)** - 系统架构设计文档
  - 核心设计哲学：优雅降级、多模态融合、认知外化
  - 系统架构图和模块设计
  - 关键设计决策和技术选型分析
  - 扩展性设计和未来演进方向

### 📊 监控与指标文档
- **[METRICS.md](METRICS.md)** - 系统指标与监控策略
  - 核心指标体系：业务指标、技术指标、质量指标
  - 监控实现策略和告警机制
  - 数据分析与异常检测
  - 性能优化和预测性分析

### 🗺️ 发展规划文档
- **[ROADMAP.md](ROADMAP.md)** - 系统演进路线图
  - 阶段性发展规划与演进策略
  - 风险管理与成功指标定义

### 🔍 经验总结文档
- **[POSTMORTEM.md](POSTMORTEM.md)** - 项目事后分析报告
  - 成功要素和关键问题识别
  - 技术决策回顾和经验教训
  - 改进行动计划和战略建议

### ⚙️ 配置与部署文档
- **[UNSPLASH_SETUP.md](UNSPLASH_SETUP.md)** - Unsplash API 配置指南
- **[GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)** - GitHub Secrets 配置指南

## 核心代码模块

### 🌅 早起打卡系统
- **[moning_main.py](moning_main.py)** - 主程序入口与命令行参数
- **[content_service.py](content_service.py)** - 内容生成服务（AI 生成 → Unsplash → 静态兜底）
- **[publishing_service.py](publishing_service.py)** - 多平台发布服务（GitHub、Telegram）
- **[config.py](config.py)** - 统一配置与环境变量管理
- **[error_handler.py](error_handler.py)** - 统一错误处理与恢复策略
- **[metrics.py](metrics.py)** - 指标与监控系统
- **[test_system.py](test_system.py)** - 系统功能测试脚本

### 📁 数据与资源
- **[OUT_DIR/](OUT_DIR/)** - 生成内容输出目录
  - 按日期组织的图片文件
  - AI 生成、智能匹配、静态备选图片分类存储

## 技术架构概览

### 系统架构
```
┌───────────────────────────┐
│        moning_main.py     │
└──────────────┬────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       ContentGenerationService         │
│  ┌────────────┐ ┌────────────┐ ┌──────┐ │
│  │ Gemini     │ │ Unsplash   │ │Static│ │
│  │ Imagen API │ │   API      │ │ Img  │ │
│  └────────────┘ └────────────┘ └──────┘ │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         PublishingService               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ GitHub  │ │Telegram │ │  Local  │   │
│  │ Issues  │ │   Bot   │ │ Storage │   │
│  └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────┘
```

### 核心设计原则
1. **优雅降级** - AI 生成 → API 匹配 → 静态备选 → 文本模式
2. **多模态融合** - 文字 + 图片 +（可选）音频
3. **认知外化** - 将个人习惯数字化为可检索的知识资产

## 快速导航

### 🚀 快速开始
1. 安装依赖：`pip install -r requirements.txt`
2. 配置环境变量：`GEMINI_IMAGEN_API_KEY`、`UNSPLASH_ACCESS_KEY`、`GITHUB_TOKEN`、`GITHUB_REPO`
3. 配置检查：`python moning_main.py --config-check`
4. 测试运行：`python moning_main.py --dry-run`

### 🔧 开发指南
1. 阅读 [DESIGN.md](DESIGN.md) 了解系统架构
2. 查看 [POSTMORTEM.md](POSTMORTEM.md) 了解最佳实践
3. 参考 [METRICS.md](METRICS.md) 建立监控体系

### 📈 产品规划
1. 查看 [ROADMAP.md](ROADMAP.md) 了解发展方向
2. 参考演进策略规划功能开发
3. 基于成功指标评估产品效果

## 关键特性

### ✨ 智能内容生成
- **AI 驱动的图片生成** - 基于诗词主题的个性化视觉内容
- **语义分析与匹配** - 中文诗词到英文关键词的智能映射
- **多源内容融合** - AI 生成、API 匹配、静态备选的三层策略

### 🔄 可靠性保障
- **多重降级机制** - 确保在外部服务失败时系统仍可用
- **错误恢复策略** - 指数退避重试和统一错误处理
- **健壮的配置管理** - 环境变量 + 默认值 + 运行时参数

### 📱 多平台集成
- **GitHub Issues** - 作为持久化的打卡记录
- **Telegram Bot** - 实时推送和多媒体分享
- **本地存储** - 内容归档和离线访问

## 项目统计

### 代码规模
- **核心模块**: moning_main.py + 5 个服务模块
- **文档覆盖**: 设计、监控、规划、总结等核心文档

### 技术栈
- **后端**: Python 3.12+
- **AI 服务**: OpenAI 兼容接口（用于 Gemini Imagen）
- **图片服务**: Unsplash API
- **通信**: Telegram Bot API, GitHub API
- **数据处理**: Pendulum, Requests, Rich, PyGithub, pyTelegramBotAPI

## 贡献指南

### 开发流程
1. **Fork 项目** 并创建功能分支
2. **阅读文档** 了解架构和设计原则
3. **编写测试** 确保代码质量
4. **更新文档** 保持文档与代码同步
5. **提交 PR** 并描述变更内容

### 代码规范
- 遵循 PEP 8 Python 代码规范
- 添加类型注解和文档字符串
- 实现适当的错误处理和日志记录
- 保持向后兼容性

### 文档维护
- 技术变更需要更新 DESIGN.md
- 新功能需要更新 ROADMAP.md
- 重要问题需要记录到 POSTMORTEM.md
- 监控指标变化需要更新 METRICS.md

## 联系方式

### 问题反馈
- **Bug 报告**: 通过 GitHub Issues 提交
- **功能请求**: 参考 ROADMAP.md 中的规划
- **文档问题**: 直接提交 PR 修复

### 技术讨论
- **架构设计**: 参考 DESIGN.md 中的设计原则
- **性能优化**: 查看 METRICS.md 中的监控策略
- **功能规划**: 基于 ROADMAP.md 中的演进路径

---

## 项目哲学

> 2024 年的主题是改变。人生艰难，尽量乐观，又是一年。

---

*本文档将随项目发展持续更新，确保信息的准确性和完整性。*
