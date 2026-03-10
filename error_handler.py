"""
统一错误处理框架
提供一致的错误分类、处理策略和恢复机制
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Type
import functools

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"          # 可忽略的错误，不影响核心功能
    MEDIUM = "medium"    # 影响部分功能，但有降级方案
    HIGH = "high"        # 影响核心功能，需要立即处理
    CRITICAL = "critical"  # 系统级错误，可能导致服务不可用


class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"              # 网络相关错误
    API = "api"                     # API 调用错误
    AUTHENTICATION = "auth"          # 认证授权错误
    CONFIGURATION = "config"         # 配置错误
    FILE_SYSTEM = "filesystem"       # 文件系统错误
    CONTENT_GENERATION = "content"   # 内容生成错误
    PUBLISHING = "publishing"        # 发布错误
    VALIDATION = "validation"        # 数据验证错误
    UNKNOWN = "unknown"             # 未知错误


@dataclass
class ErrorContext:
    """错误上下文信息"""
    operation: str                    # 操作名称
    component: str                   # 组件名称
    user_data: Dict[str, Any] = None # 用户相关数据
    system_data: Dict[str, Any] = None # 系统相关数据

    def __post_init__(self):
        if self.user_data is None:
            self.user_data = {}
        if self.system_data is None:
            self.system_data = {}


class MoningException(Exception):
    """Moning 项目统一异常基类"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recoverable: bool = True,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.context = context or ErrorContext("unknown", "unknown")
        self.original_error = original_error
        self.timestamp = time.time()

        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于日志记录和监控"""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
            "operation": self.context.operation,
            "component": self.context.component,
            "original_error": str(self.original_error) if self.original_error else None
        }


class NetworkError(MoningException):
    """网络相关错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class APIError(MoningException):
    """API 调用错误"""
    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        self.status_code = status_code
        super().__init__(message, category=ErrorCategory.API, **kwargs)


class AuthenticationError(MoningException):
    """认证错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class ConfigurationError(MoningException):
    """配置错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class ContentGenerationError(MoningException):
    """内容生成错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CONTENT_GENERATION, **kwargs)


class PublishingError(MoningException):
    """发布错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.PUBLISHING, **kwargs)


class ErrorRecoveryStrategy(ABC):
    """错误恢复策略抽象基类"""

    @abstractmethod
    def can_handle(self, error: MoningException) -> bool:
        """判断是否可以处理该错误"""
        pass

    @abstractmethod
    def recover(self, error: MoningException, context: Dict[str, Any]) -> Any:
        """执行错误恢复"""
        pass


class RetryStrategy(ErrorRecoveryStrategy):
    """重试策略"""

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, backoff_factor: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor

    def can_handle(self, error: MoningException) -> bool:
        return error.recoverable and error.category in [
            ErrorCategory.NETWORK,
            ErrorCategory.API,
            ErrorCategory.CONTENT_GENERATION
        ]

    def recover(self, error: MoningException, context: Dict[str, Any]) -> Any:
        operation = context.get('operation')
        if not operation:
            raise error

        for attempt in range(self.max_attempts):
            try:
                logger.info(f"Retry attempt {attempt + 1}/{self.max_attempts} for {error.context.operation}")
                return operation()
            except Exception as e:
                if attempt == self.max_attempts - 1:
                    raise e

                delay = self.base_delay * (self.backoff_factor ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)


class FallbackStrategy(ErrorRecoveryStrategy):
    """降级策略"""

    def __init__(self, fallback_operations: List[Callable]):
        self.fallback_operations = fallback_operations

    def can_handle(self, error: MoningException) -> bool:
        return error.recoverable and len(self.fallback_operations) > 0

    def recover(self, error: MoningException, context: Dict[str, Any]) -> Any:
        for i, fallback_op in enumerate(self.fallback_operations):
            try:
                logger.info(f"Trying fallback operation {i + 1}/{len(self.fallback_operations)}")
                return fallback_op()
            except Exception as e:
                logger.warning(f"Fallback operation {i + 1} failed: {e}")
                if i == len(self.fallback_operations) - 1:
                    raise error


class DefaultValueStrategy(ErrorRecoveryStrategy):
    """默认值策略"""

    def __init__(self, default_value: Any):
        self.default_value = default_value

    def can_handle(self, error: MoningException) -> bool:
        return error.recoverable

    def recover(self, error: MoningException, context: Dict[str, Any]) -> Any:
        logger.warning(f"Using default value for {error.context.operation}: {self.default_value}")
        return self.default_value


class ErrorHandler:
    """统一错误处理器"""

    def __init__(self):
        self.strategies: List[ErrorRecoveryStrategy] = []
        self.error_metrics: Dict[str, int] = {}

    def add_strategy(self, strategy: ErrorRecoveryStrategy):
        """添加错误恢复策略"""
        self.strategies.append(strategy)

    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        operation: Optional[Callable] = None
    ) -> Any:
        """处理错误"""

        # 转换为 MoningException
        if not isinstance(error, MoningException):
            moning_error = self._convert_to_moning_exception(error, context)
        else:
            moning_error = error

        # 记录错误指标
        self._record_error_metrics(moning_error)

        # 记录错误日志
        self._log_error(moning_error)

        # 尝试错误恢复
        if moning_error.recoverable:
            for strategy in self.strategies:
                if strategy.can_handle(moning_error):
                    try:
                        recovery_context = {'operation': operation} if operation else {}
                        return strategy.recover(moning_error, recovery_context)
                    except Exception as recovery_error:
                        logger.error(f"Error recovery failed: {recovery_error}")

        # 如果无法恢复，重新抛出异常
        raise moning_error

    def _convert_to_moning_exception(self, error: Exception, context: ErrorContext) -> MoningException:
        """将普通异常转换为 MoningException"""

        # 根据异常类型进行分类
        if isinstance(error, (ConnectionError, TimeoutError)):
            return NetworkError(
                str(error),
                context=context,
                original_error=error
            )
        elif "401" in str(error) or "403" in str(error) or "unauthorized" in str(error).lower():
            return AuthenticationError(
                str(error),
                context=context,
                original_error=error
            )
        elif "404" in str(error) or "400" in str(error):
            return APIError(
                str(error),
                context=context,
                original_error=error
            )
        else:
            return MoningException(
                str(error),
                context=context,
                original_error=error
            )

    def _record_error_metrics(self, error: MoningException):
        """记录错误指标"""
        key = f"{error.category.value}_{error.severity.value}"
        self.error_metrics[key] = self.error_metrics.get(key, 0) + 1

    def _log_error(self, error: MoningException):
        """记录错误日志"""
        log_data = error.to_dict()

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error in {error.context.component}: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error in {error.context.component}: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error in {error.context.component}: {error.message}", extra=log_data)
        else:
            logger.info(f"Low severity error in {error.context.component}: {error.message}", extra=log_data)

    def get_error_metrics(self) -> Dict[str, int]:
        """获取错误指标"""
        return self.error_metrics.copy()


# 全局错误处理器实例
error_handler = ErrorHandler()

# 添加默认策略
error_handler.add_strategy(RetryStrategy(max_attempts=3, base_delay=1.0))


def handle_errors(
    component: str,
    operation: str,
    fallback_value: Any = None,
    retry_attempts: int = 3
):
    """错误处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(operation=operation, component=component)

            try:
                return func(*args, **kwargs)
            except Exception as e:
                if fallback_value is not None:
                    # 添加默认值策略
                    temp_handler = ErrorHandler()
                    temp_handler.add_strategy(RetryStrategy(max_attempts=retry_attempts))
                    temp_handler.add_strategy(DefaultValueStrategy(fallback_value))

                    return temp_handler.handle_error(e, context, lambda: func(*args, **kwargs))
                else:
                    return error_handler.handle_error(e, context, lambda: func(*args, **kwargs))

        return wrapper
    return decorator


def safe_api_call(
    func: Callable,
    context: ErrorContext,
    max_retries: int = 3,
    fallback_result: Any = None
) -> Any:
    """安全的 API 调用包装器"""

    temp_handler = ErrorHandler()
    temp_handler.add_strategy(RetryStrategy(max_attempts=max_retries))

    if fallback_result is not None:
        temp_handler.add_strategy(DefaultValueStrategy(fallback_result))

    try:
        return func()
    except Exception as e:
        return temp_handler.handle_error(e, context, func)


# 常用的错误处理函数
def handle_api_error(error: Exception, component: str, operation: str) -> MoningException:
    """处理 API 错误的便捷函数"""
    context = ErrorContext(operation=operation, component=component)

    if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        status_code = error.response.status_code
        if status_code in [401, 403]:
            return AuthenticationError(f"API authentication failed: {error}", context=context)
        elif status_code >= 500:
            return APIError(f"API server error: {error}", status_code=status_code, context=context)
        else:
            return APIError(f"API client error: {error}", status_code=status_code, context=context)
    else:
        return NetworkError(f"Network error during API call: {error}", context=context)


def handle_content_generation_error(error: Exception, generator: str) -> ContentGenerationError:
    """处理内容生成错误的便捷函数"""
    context = ErrorContext(operation="content_generation", component=generator)
    return ContentGenerationError(f"Content generation failed: {error}", context=context)


def handle_publishing_error(error: Exception, platform: str) -> PublishingError:
    """处理发布错误的便捷函数"""
    context = ErrorContext(operation="publishing", component=platform)
    return PublishingError(f"Publishing to {platform} failed: {error}", context=context)