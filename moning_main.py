"""
Moning 项目重构后的主程序
整合模块化的配置管理、内容生成、错误处理、监控和发布服务
"""

import argparse
import logging
import sys
import urllib.parse
from typing import Optional
import requests
from pathlib import Path

# 导入新的模块化组件
from config import load_config, MoningConfig
from content_service import ContentGenerationService, ContentRequest, get_sentence_from_api
from publishing_service import PublishingService, create_checkin_content
from error_handler import handle_errors, ErrorContext, ConfigurationError
from metrics import init_metrics, get_metrics, track_performance

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('moning.log')
    ]
)
logger = logging.getLogger(__name__)


class MoningApp:
    """Moning 应用主类"""

    def __init__(self, config: MoningConfig):
        self.config = config

        # 初始化服务
        self.content_service = ContentGenerationService(config)
        self.publishing_service = PublishingService(config)

        # 初始化指标系统
        init_metrics(config.app.output_dir)
        self.metrics = get_metrics()

    @track_performance(component="moning_app", operation="daily_checkin")
    def run_daily_checkin(self, weather_message: str = "", dry_run: bool = False) -> bool:
        """执行每日打卡流程"""

        logger.info("Starting daily check-in process")

        try:
            # 1. 获取诗句
            sentence = self._get_daily_sentence()
            logger.info(f"Got daily sentence: {sentence[:50]}...")

            # 2. 生成内容
            content_request = ContentRequest(sentence=sentence)
            generated_content = self.content_service.generate_content(content_request)

            if not generated_content:
                logger.warning("Failed to generate content, using text-only mode")

            # 记录内容生成指标
            if self.metrics:
                success = generated_content is not None
                source = generated_content.source if generated_content else "none"
                self.metrics.record_content_generation("overall", success, 0, source)

            # 3. 获取天气与每日格言
            auto_weather = weather_message or self._get_weather_message()
            daily_quote = self._get_daily_quote()

            # 4. 创建发布内容
            publish_content = create_checkin_content(
                sentence=sentence,
                image_path=generated_content.image_path if generated_content else None,
                image_url=generated_content.image_url if generated_content else None,
                weather_message=auto_weather,
                daily_quote=daily_quote,
                timezone=self.config.app.timezone
            )

            # 5. 发布内容
            if dry_run:
                logger.info("DRY RUN MODE - Content would be published:")
                logger.info(f"Text: {publish_content.text}")
                logger.info(f"Image: {publish_content.image_path or publish_content.image_url}")

                # 记录业务指标
                if self.metrics:
                    self.metrics.record_daily_checkin(True)

                return True
            else:
                publish_results = self.publishing_service.publish_content(publish_content)

                # 检查发布结果
                successful_publishes = [r for r in publish_results if r.success]

                if successful_publishes:
                    logger.info(f"Successfully published to {len(successful_publishes)} platforms")

                    # 记录业务指标
                    if self.metrics:
                        self.metrics.record_daily_checkin(True)

                    return True
                else:
                    logger.error("Failed to publish to any platform")

                    # 记录业务指标
                    if self.metrics:
                        self.metrics.record_daily_checkin(False)

                    return False

        except Exception as e:
            logger.error(f"Daily check-in failed: {e}")

            # 记录错误指标
            if self.metrics:
                self.metrics.record_error("moning_app", "checkin_error", "high")
                self.metrics.record_daily_checkin(False)

            raise

    @handle_errors(component="moning_app", operation="get_sentence")
    def _get_daily_sentence(self) -> str:
        """获取每日诗句"""

        # 尝试从 API 获取
        sentence = get_sentence_from_api(self.config.app.sentence_api)

        if sentence:
            logger.info("Successfully got sentence from API")
            return sentence
        else:
            logger.warning("Failed to get sentence from API, using default")
            return self.config.app.default_sentence

    def _get_weather_message(self) -> str:
        """获取天气信息"""
        city_code = self.config.app.weather_city_code
        if not city_code:
            return ""

        base = self.config.app.weather_api_base.rstrip("/")
        weather_api = f"{base}/api/weather/city/{city_code}"
        default_weather = "未查询到天气"
        template = "今天是{date} {week}的天气是{type}，{high}，{low}，空气量指数{aqi},tips:{notice}"

        try:
            response = requests.get(weather_api, timeout=10)
            if response.ok:
                data = response.json()
                forecast = (data.get("data") or {}).get("forecast") or []
                if forecast:
                    today = forecast[0]
                    return template.format(
                        date=today.get("ymd", ""),
                        week=today.get("week", ""),
                        type=today.get("type", ""),
                        high=today.get("high", ""),
                        low=today.get("low", ""),
                        aqi=today.get("aqi", ""),
                        notice=today.get("notice", "")
                    ).strip()
            return default_weather
        except Exception as e:
            logger.warning(f"Failed to get weather: {e}")
            return default_weather

    def _get_daily_quote(self) -> str:
        """获取每日格言"""
        api_key = self.config.app.tian_api_key
        if not api_key:
            return ""

        base_url = self.config.app.tian_api_url
        try:
            params = {"key": api_key}
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            response = requests.get(url, timeout=10)
            if not response.ok:
                return ""

            data = response.json()
            news = data.get("newslist") or []
            if not news:
                return ""

            item = news[0]
            content = (
                item.get("content")
                or item.get("saying")
                or item.get("title")
                or item.get("note")
                or ""
            )
            author = item.get("author") or item.get("source") or item.get("origin") or ""

            if content and author:
                return f"{content} —— {author}"
            return content
        except Exception as e:
            logger.warning(f"Failed to get daily quote: {e}")
            return ""

    def get_system_status(self) -> dict:
        """获取系统状态"""

        status = {
            "timestamp": None,
            "config": {
                "valid": True,
                "errors": []
            },
            "services": {
                "content_generation": {},
                "publishing": {}
            },
            "metrics": {}
        }

        try:
            import time
            status["timestamp"] = time.time()

            # 检查配置
            try:
                config_errors = self.config.validate()
                status["config"]["errors"] = config_errors
                status["config"]["valid"] = len(config_errors) == 0
            except Exception as e:
                status["config"]["valid"] = False
                status["config"]["errors"] = [str(e)]

            # 检查内容生成服务
            available_generators = self.content_service.get_available_generators()
            status["services"]["content_generation"] = {
                "available_generators": available_generators,
                "total_generators": len(self.content_service.generators)
            }

            # 检查发布服务
            available_platforms = self.publishing_service.get_available_platforms()
            publisher_tests = self.publishing_service.test_publishers()
            status["services"]["publishing"] = {
                "available_platforms": available_platforms,
                "publisher_tests": publisher_tests
            }

            # 获取指标
            if self.metrics:
                status["metrics"] = self.metrics.generate_health_report()

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            status["error"] = str(e)

        return status

    def cleanup(self):
        """清理资源"""
        try:
            if self.metrics:
                self.metrics.flush()
                logger.info("Metrics flushed successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup: {e}")


def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""

    parser = argparse.ArgumentParser(
        description="Moning - 智能化个人习惯养成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python moning_main.py --dry-run                    # 测试模式
  python moning_main.py --weather "晴天 20°C"        # 带天气信息
  python moning_main.py --status                     # 查看系统状态

环境变量配置:
  GEMINI_IMAGEN_API_KEY - Gemini Imagen API 密钥
  GEMINI_IMAGEN_API_BASE - Gemini Imagen API 地址（可选覆盖）
  FENXI_MODEL           - 诗词主题分析模型（可选覆盖）
  UNSPLASH_ACCESS_KEY   - Unsplash API 密钥
  GITHUB_TOKEN          - GitHub 访问令牌
  GITHUB_REPO           - GitHub 仓库名 (格式: owner/repo)
  TG_TOKEN              - Telegram Bot 令牌 (可选)
  TG_CHAT_ID            - Telegram 聊天 ID (可选)
  TIAN_API_KEY          - 天行数据每日格言 Key (可选)
        """
    )

    # 主要操作参数
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="测试模式，不实际发布内容"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="显示系统状态信息"
    )

    # 内容参数
    parser.add_argument(
        "--weather",
        type=str,
        default="",
        help="天气信息"
    )

    # 覆盖配置参数
    parser.add_argument(
        "--github-token",
        type=str,
        help="GitHub 访问令牌 (覆盖环境变量)"
    )

    parser.add_argument(
        "--repo-name",
        type=str,
        help="GitHub 仓库名 (覆盖环境变量)"
    )

    parser.add_argument(
        "--telegram-token",
        type=str,
        help="Telegram Bot 令牌 (覆盖环境变量)"
    )

    parser.add_argument(
        "--telegram-chat-id",
        type=str,
        help="Telegram 聊天 ID (覆盖环境变量)"
    )

    # 调试参数
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志输出"
    )

    parser.add_argument(
        "--config-check",
        action="store_true",
        help="仅检查配置是否正确"
    )

    return parser


def override_config_from_args(config: MoningConfig, args: argparse.Namespace) -> MoningConfig:
    """根据命令行参数覆盖配置"""

    if args.github_token:
        config.github.token = args.github_token

    if args.repo_name:
        config.github.repo_name = args.repo_name

    if args.telegram_token:
        config.telegram.token = args.telegram_token

    if args.telegram_chat_id:
        config.telegram.chat_id = args.telegram_chat_id

    return config


def main():
    """主函数"""

    # 解析命令行参数
    parser = create_argument_parser()
    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # 加载配置
        logger.info("Loading configuration...")

        # 对于配置检查、状态查看和干运行，使用非严格模式
        strict_mode = not (args.config_check or args.status or args.dry_run)
        config = load_config(strict=strict_mode)

        # 根据命令行参数覆盖配置
        config = override_config_from_args(config, args)

        # 配置检查模式
        if args.config_check:
            errors = config.validate()
            if errors:
                logger.error("Configuration errors found:")
                for error in errors:
                    logger.error(f"  - {error}")
                sys.exit(1)
            else:
                logger.info("Configuration is valid")
                sys.exit(0)

        # 创建应用实例
        app = MoningApp(config)

        # 状态查看模式
        if args.status:
            status = app.get_system_status()

            print("\n=== Moning 系统状态 ===")
            print(f"时间戳: {status.get('timestamp', 'N/A')}")

            print(f"\n配置状态: {'✅ 有效' if status['config']['valid'] else '❌ 无效'}")
            if status['config']['errors']:
                for error in status['config']['errors']:
                    print(f"  - {error}")

            print(f"\n内容生成服务:")
            cg = status['services']['content_generation']
            print(f"  可用生成器: {len(cg.get('available_generators', []))}/{cg.get('total_generators', 0)}")
            for gen in cg.get('available_generators', []):
                print(f"    ✅ {gen}")

            print(f"\n发布服务:")
            pub = status['services']['publishing']
            print(f"  可用平台: {len(pub.get('available_platforms', []))}")
            for platform, available in pub.get('publisher_tests', {}).items():
                status_icon = "✅" if available else "❌"
                print(f"    {status_icon} {platform}")

            if 'metrics' in status and status['metrics']:
                print(f"\n系统指标:")
                metrics = status['metrics']
                if 'business' in metrics:
                    business = metrics['business']
                    print(f"  今日打卡: {business.get('daily_checkins', 0)}")
                    print(f"  今日学词: {business.get('words_learned', 0)}")

            sys.exit(0)

        # 执行每日打卡
        logger.info("Starting Moning daily check-in")
        success = app.run_daily_checkin(
            weather_message=args.weather,
            dry_run=args.dry_run
        )

        if success:
            logger.info("Daily check-in completed successfully")
            sys.exit(0)
        else:
            logger.error("Daily check-in failed")
            sys.exit(1)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your environment variables and configuration")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # 清理资源
        try:
            if 'app' in locals():
                app.cleanup()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    main()
