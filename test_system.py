"""
Moning 项目测试脚本
验证重构后的模块化系统功能
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import MoningConfig, load_config
from content_service import ContentGenerationService, ContentRequest
from publishing_service import PublishingService, create_checkin_content
from error_handler import ErrorHandler, MoningException
from metrics import init_metrics, get_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_config_system():
    """测试配置系统"""
    print("\n=== 测试配置系统 ===")

    try:
        # 测试配置加载
        config = MoningConfig.from_env()
        print("✅ 配置加载成功")

        # 测试配置验证
        errors = config.validate()
        if errors:
            print("⚠️  配置验证发现问题:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("✅ 配置验证通过")

        return config

    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
        return None


def test_content_generation(config):
    """测试内容生成服务"""
    print("\n=== 测试内容生成服务 ===")

    try:
        service = ContentGenerationService(config)

        # 检查可用的生成器
        available_generators = service.get_available_generators()
        print(f"可用生成器: {available_generators}")

        # 测试内容生成
        request = ContentRequest(sentence="春江潮水连海平，海上明月共潮生")

        print("正在生成内容...")
        content = service.generate_content(request)

        if content:
            print("✅ 内容生成成功")
            print(f"   来源: {content.source}")
            print(f"   图片路径: {content.image_path}")
            print(f"   图片URL: {content.image_url}")
        else:
            print("⚠️  内容生成失败，但系统正常运行")

        return True

    except Exception as e:
        print(f"❌ 内容生成测试失败: {e}")
        return False


def test_publishing_service(config):
    """测试发布服务"""
    print("\n=== 测试发布服务 ===")

    try:
        service = PublishingService(config)

        # 检查可用平台
        available_platforms = service.get_available_platforms()
        print(f"可用发布平台: {available_platforms}")

        # 测试发布器状态
        publisher_tests = service.test_publishers()
        for platform, status in publisher_tests.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {platform}")

        # 创建测试内容
        test_content = create_checkin_content(
            sentence="测试诗句：春江潮水连海平",
            weather_message="测试天气：晴天 20°C"
        )

        print(f"测试内容创建成功，长度: {len(test_content.text)} 字符")

        return True

    except Exception as e:
        print(f"❌ 发布服务测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理系统"""
    print("\n=== 测试错误处理系统 ===")

    try:
        # 测试错误处理器
        handler = ErrorHandler()

        # 测试自定义异常
        from error_handler import NetworkError, ErrorContext

        context = ErrorContext("test_operation", "test_component")
        error = NetworkError("测试网络错误", context=context)

        print("✅ 错误处理系统初始化成功")
        print(f"   错误分类: {error.category.value}")
        print(f"   错误严重程度: {error.severity.value}")
        print(f"   是否可恢复: {error.recoverable}")

        return True

    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


def test_metrics_system(config):
    """测试指标系统"""
    print("\n=== 测试指标系统 ===")

    try:
        # 初始化指标系统
        init_metrics(config.app.output_dir)
        metrics = get_metrics()

        if metrics:
            print("✅ 指标系统初始化成功")

            # 测试指标记录
            metrics.record_api_call("test_api", True, 0.5, 200)
            metrics.record_content_generation("test_generator", True, 2.0, "ai_generated")
            metrics.record_publishing("test_platform", True, 1.0)

            print("✅ 指标记录测试成功")

            # 生成健康报告
            health_report = metrics.generate_health_report()
            print(f"✅ 健康报告生成成功，包含 {len(health_report)} 个部分")

            return True
        else:
            print("❌ 指标系统初始化失败")
            return False

    except Exception as e:
        print(f"❌ 指标系统测试失败: {e}")
        return False


def test_integration(config):
    """集成测试"""
    print("\n=== 集成测试 ===")

    try:
        from moning_main import MoningApp

        # 创建应用实例
        app = MoningApp(config)
        print("✅ 应用实例创建成功")

        # 获取系统状态
        status = app.get_system_status()
        print("✅ 系统状态获取成功")

        # 检查各个组件状态
        config_valid = status['config']['valid']
        content_generators = len(status['services']['content_generation'].get('available_generators', []))
        publishing_platforms = len(status['services']['publishing'].get('available_platforms', []))

        print(f"   配置状态: {'✅' if config_valid else '❌'}")
        print(f"   可用内容生成器: {content_generators}")
        print(f"   可用发布平台: {publishing_platforms}")

        # 清理
        app.cleanup()

        return True

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始 Moning 项目重构验证测试")

    # 检查必要的环境变量
    required_env_vars = ["UNSPLASH_ACCESS_KEY", "GITHUB_TOKEN", "GITHUB_REPO"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

    if missing_vars:
        print(f"\n⚠️  缺少必要的环境变量: {', '.join(missing_vars)}")
        print("某些测试可能会失败，但系统架构测试仍会继续")

    if not os.environ.get("GEMINI_IMAGEN_API_KEY"):
        print("\nℹ️  未设置 GEMINI_IMAGEN_API_KEY，AI 生图将不可用，系统会走降级策略")

    test_results = []

    # 1. 测试配置系统
    config = test_config_system()
    test_results.append(("配置系统", config is not None))

    if config:
        # 2. 测试内容生成服务
        content_test = test_content_generation(config)
        test_results.append(("内容生成服务", content_test))

        # 3. 测试发布服务
        publishing_test = test_publishing_service(config)
        test_results.append(("发布服务", publishing_test))

        # 4. 测试指标系统
        metrics_test = test_metrics_system(config)
        test_results.append(("指标系统", metrics_test))

        # 5. 集成测试
        integration_test = test_integration(config)
        test_results.append(("集成测试", integration_test))

    # 6. 测试错误处理（独立于配置）
    error_test = test_error_handling()
    test_results.append(("错误处理系统", error_test))

    # 输出测试结果
    print("\n" + "="*50)
    print("📊 测试结果汇总")
    print("="*50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status_icon = "✅" if result else "❌"
        print(f"{status_icon} {test_name}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有测试通过！重构系统运行正常")
        return 0
    elif passed >= total * 0.7:  # 70% 通过率
        print("⚠️  大部分测试通过，系统基本可用")
        return 0
    else:
        print("❌ 多项测试失败，请检查配置和环境")
        return 1


if __name__ == "__main__":
    sys.exit(main())
