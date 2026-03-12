"""
发布服务抽象层
提供统一的多平台内容发布接口和管理
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pendulum
import requests
import telebot
from telebot.types import InputMediaPhoto
from github import Github

from config import MoningConfig
from error_handler import handle_errors, PublishingError, ErrorContext
from metrics import track_performance, get_metrics

logger = logging.getLogger(__name__)


@dataclass
class PublishContent:
    """发布内容"""
    text: str
    image_path: Optional[Path] = None
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    platform: str
    message: str = ""
    url: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Publisher(ABC):
    """发布器抽象基类"""

    def __init__(self, config: MoningConfig):
        self.config = config

    @abstractmethod
    def is_available(self) -> bool:
        """检查发布器是否可用"""
        pass

    @abstractmethod
    def publish(self, content: PublishContent) -> PublishResult:
        """发布内容"""
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """获取平台名称"""
        pass


class GitHubPublisher(Publisher):
    """GitHub Issues 发布器"""

    def __init__(self, config: MoningConfig):
        super().__init__(config)
        self.client = None
        if config.github.token:
            self.client = Github(config.github.token)

    def is_available(self) -> bool:
        return (
            self.client is not None and
            self.config.github.token is not None and
            self.config.github.repo_name is not None
        )

    def get_platform_name(self) -> str:
        return "github"

    @handle_errors(component="github_publisher", operation="publish_to_github")
    @track_performance(component="publishing", operation="github_publish")
    def publish(self, content: PublishContent) -> PublishResult:
        if not self.is_available():
            return PublishResult(
                success=False,
                platform="github",
                message="GitHub publisher not available"
            )

        try:
            # 获取仓库
            repo = self.client.get_repo(self.config.github.repo_name)

            # 获取指定的 Issue
            issue = repo.get_issue(self.config.github.issue_number)

            # 构建评论内容
            comment_body = self._build_comment_body(content)

            # 发布评论
            comment = issue.create_comment(comment_body)

            # 记录指标
            metrics = get_metrics()
            if metrics:
                metrics.record_publishing("github", True, 0)  # GitHub API 通常很快

            return PublishResult(
                success=True,
                platform="github",
                message="Successfully published to GitHub Issues",
                url=comment.html_url,
                metadata={
                    "issue_number": self.config.github.issue_number,
                    "comment_id": comment.id
                }
            )

        except Exception as e:
            logger.error(f"Failed to publish to GitHub: {e}")

            # 记录指标
            metrics = get_metrics()
            if metrics:
                metrics.record_publishing("github", False, 0)
                metrics.record_error("github_publisher", "publish_error", "medium")

            raise PublishingError(
                f"GitHub publishing failed: {e}",
                context=ErrorContext("publish_to_github", "github_publisher")
            )

    def _build_comment_body(self, content: PublishContent) -> str:
        """构建 GitHub Issue 评论内容"""
        body_parts = [content.text]

        # 添加图片
        if content.image_url:
            body_parts.append(f"\n![Generated Image]({content.image_url})")
        elif content.image_path and content.image_path.exists():
            # 对于本地图片，我们需要先上传到某个图床或使用 GitHub 的方式
            # 这里暂时只添加文件路径信息
            body_parts.append(f"\n*Image saved locally: {content.image_path.name}*")

        # 添加元数据
        if content.metadata:
            body_parts.append("\n---")
            for key, value in content.metadata.items():
                if key not in ["sensitive_info"]:  # 过滤敏感信息
                    body_parts.append(f"**{key}**: {value}")

        return "\n".join(body_parts)


class TelegramPublisher(Publisher):
    """Telegram Bot 发布器"""

    def __init__(self, config: MoningConfig):
        super().__init__(config)
        self.bot = None
        if config.telegram.token:
            self.bot = telebot.TeleBot(config.telegram.token)

    def is_available(self) -> bool:
        return (
            self.bot is not None and
            self.config.telegram.token is not None and
            self.config.telegram.chat_id is not None
        )

    def get_platform_name(self) -> str:
        return "telegram"

    @handle_errors(component="telegram_publisher", operation="publish_to_telegram")
    @track_performance(component="publishing", operation="telegram_publish")
    def publish(self, content: PublishContent) -> PublishResult:
        if not self.is_available():
            return PublishResult(
                success=False,
                platform="telegram",
                message="Telegram publisher not available"
            )

        try:
            start_time = time.time()

            # 如果有图片，发送图片和文字
            if content.image_path and content.image_path.exists():
                with open(content.image_path, 'rb') as photo:
                    message = self.bot.send_photo(
                        chat_id=self.config.telegram.chat_id,
                        photo=photo,
                        caption=content.text,
                        parse_mode='Markdown'
                    )
            elif content.image_url:
                # 使用图片 URL
                try:
                    message = self.bot.send_photo(
                        chat_id=self.config.telegram.chat_id,
                        photo=content.image_url,
                        caption=content.text,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Telegram send_photo failed, fallback to text-only: {e}")
                    message = self.bot.send_message(
                        chat_id=self.config.telegram.chat_id,
                        text=content.text,
                        parse_mode='Markdown'
                    )
            else:
                # 只发送文字
                message = self.bot.send_message(
                    chat_id=self.config.telegram.chat_id,
                    text=content.text,
                    parse_mode='Markdown'
                )

            duration = time.time() - start_time

            # 记录指标
            metrics = get_metrics()
            if metrics:
                metrics.record_publishing("telegram", True, duration)

            return PublishResult(
                success=True,
                platform="telegram",
                message="Successfully published to Telegram",
                metadata={
                    "message_id": message.message_id,
                    "chat_id": self.config.telegram.chat_id
                }
            )

        except Exception as e:
            logger.error(f"Failed to publish to Telegram: {e}")

            # 记录指标
            metrics = get_metrics()
            if metrics:
                metrics.record_publishing("telegram", False, 0)
                metrics.record_error("telegram_publisher", "publish_error", "medium")

            raise PublishingError(
                f"Telegram publishing failed: {e}",
                context=ErrorContext("publish_to_telegram", "telegram_publisher")
            )


class LocalFilePublisher(Publisher):
    """本地文件发布器（备选方案）"""

    def __init__(self, config: MoningConfig):
        super().__init__(config)
        self.output_dir = config.app.output_dir

    def is_available(self) -> bool:
        return True  # 本地文件发布器总是可用

    def get_platform_name(self) -> str:
        return "local_file"

    @handle_errors(component="local_publisher", operation="publish_to_file")
    @track_performance(component="publishing", operation="local_publish")
    def publish(self, content: PublishContent) -> PublishResult:
        try:
            # 创建今日目录
            today = pendulum.now(self.config.app.timezone).format("YYYY-MM-DD")
            daily_dir = self.output_dir / today
            daily_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = int(time.time())
            filename = f"checkin_{timestamp}.md"
            filepath = daily_dir / filename

            # 写入内容
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# 打卡记录 - {today}\n\n")
                f.write(content.text)
                f.write("\n\n")

                if content.image_path:
                    f.write(f"![Image]({content.image_path.name})\n\n")
                elif content.image_url:
                    f.write(f"![Image]({content.image_url})\n\n")

                if content.metadata:
                    f.write("## 元数据\n\n")
                    for key, value in content.metadata.items():
                        f.write(f"- **{key}**: {value}\n")

            return PublishResult(
                success=True,
                platform="local_file",
                message=f"Successfully saved to {filepath}",
                url=str(filepath),
                metadata={"filepath": str(filepath)}
            )

        except Exception as e:
            logger.error(f"Failed to publish to local file: {e}")
            raise PublishingError(
                f"Local file publishing failed: {e}",
                context=ErrorContext("publish_to_file", "local_publisher")
            )


class PublishingService:
    """发布服务 - 管理多平台发布"""

    def __init__(self, config: MoningConfig):
        self.config = config
        self.publishers = [
            GitHubPublisher(config),
            TelegramPublisher(config),
            LocalFilePublisher(config)  # 作为最后的备选方案
        ]

    def publish_content(
        self,
        content: PublishContent,
        platforms: Optional[List[str]] = None,
        require_all_success: bool = False
    ) -> List[PublishResult]:
        """发布内容到指定平台"""

        if platforms is None:
            # 默认发布到所有可用平台
            target_publishers = [p for p in self.publishers if p.is_available()]
        else:
            # 发布到指定平台
            target_publishers = [
                p for p in self.publishers
                if p.get_platform_name() in platforms and p.is_available()
            ]

        if not target_publishers:
            logger.warning("No available publishers found")
            return []

        results = []
        successful_count = 0

        for publisher in target_publishers:
            platform_name = publisher.get_platform_name()
            logger.info(f"Publishing to {platform_name}")

            try:
                result = publisher.publish(content)
                results.append(result)

                if result.success:
                    successful_count += 1
                    logger.info(f"Successfully published to {platform_name}")
                else:
                    logger.warning(f"Failed to publish to {platform_name}: {result.message}")

            except Exception as e:
                logger.error(f"Error publishing to {platform_name}: {e}")
                results.append(PublishResult(
                    success=False,
                    platform=platform_name,
                    message=f"Publishing error: {e}"
                ))

        # 检查是否满足要求
        if require_all_success and successful_count < len(target_publishers):
            logger.error(f"Required all platforms to succeed, but only {successful_count}/{len(target_publishers)} succeeded")

        logger.info(f"Publishing completed: {successful_count}/{len(target_publishers)} platforms succeeded")
        return results

    def get_available_platforms(self) -> List[str]:
        """获取可用的发布平台列表"""
        return [
            publisher.get_platform_name()
            for publisher in self.publishers
            if publisher.is_available()
        ]

    def test_publishers(self) -> Dict[str, bool]:
        """测试所有发布器的可用性"""
        results = {}

        for publisher in self.publishers:
            platform_name = publisher.get_platform_name()
            try:
                # 简单的可用性测试
                available = publisher.is_available()
                results[platform_name] = available

                if available:
                    logger.info(f"{platform_name} publisher is available")
                else:
                    logger.warning(f"{platform_name} publisher is not available")

            except Exception as e:
                logger.error(f"Error testing {platform_name} publisher: {e}")
                results[platform_name] = False

        return results


def create_checkin_content(
    sentence: str,
    image_path: Optional[Path] = None,
    image_url: Optional[str] = None,
    weather_message: str = "",
    timezone: str = "Asia/Shanghai"
) -> PublishContent:
    """创建打卡内容"""

    # 获取当前时间和年度进度
    now = pendulum.now(timezone)
    get_up_time = now.format("YYYY-MM-DD HH:mm:ss")

    # 计算年度进度
    year_start = pendulum.datetime(now.year, 1, 1, tz=timezone)
    year_end = pendulum.datetime(now.year + 1, 1, 1, tz=timezone)
    year_total_seconds = (year_end - year_start).total_seconds()
    year_passed_seconds = (now - year_start).total_seconds()
    year_progress_percent = (year_passed_seconds / year_total_seconds) * 100

    # 生成进度条
    progress_bar_length = 20
    filled_length = int(progress_bar_length * year_progress_percent / 100)
    progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)

    year_progress = f"{progress_bar} {year_progress_percent:.1f}% ({now.day_of_year}/365)"

    # 构建消息内容
    message_parts = [
        f"#Now 记录时间是--{get_up_time}",
        "",
        "今天的一句诗:",
        sentence,
        "",
        "📅 年度进度:",
        year_progress
    ]

    if weather_message:
        message_parts.extend(["", "🌤️ 天气信息:", weather_message])

    text = "\r\n".join(message_parts)

    return PublishContent(
        text=text,
        image_path=image_path,
        image_url=image_url,
        metadata={
            "timestamp": get_up_time,
            "year_progress": year_progress_percent,
            "day_of_year": now.day_of_year,
            "timezone": timezone
        }
    )
