"""
监控和指标收集系统
提供系统性的性能监控、错误追踪和业务指标收集
"""

import logging
import time
import threading
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"        # 计数器：只增不减
    GAUGE = "gauge"           # 仪表盘：可增可减的瞬时值
    HISTOGRAM = "histogram"    # 直方图：分布统计
    TIMER = "timer"           # 计时器：执行时间统计


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation: str
    duration: float
    success: bool
    timestamp: float
    component: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessMetrics:
    """业务指标"""
    event: str
    count: int
    timestamp: float
    properties: Dict[str, Any] = field(default_factory=dict)


class MetricCollector(ABC):
    """指标收集器抽象基类"""

    @abstractmethod
    def collect(self, metric: MetricPoint):
        """收集指标"""
        pass

    @abstractmethod
    def flush(self):
        """刷新指标到存储"""
        pass


class InMemoryCollector(MetricCollector):
    """内存指标收集器"""

    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.lock = threading.Lock()

    def collect(self, metric: MetricPoint):
        with self.lock:
            self.metrics[metric.name].append(metric)

    def flush(self):
        # 内存收集器不需要刷新
        pass

    def get_metrics(self, name: str, since: Optional[float] = None) -> List[MetricPoint]:
        """获取指标数据"""
        with self.lock:
            metrics = list(self.metrics.get(name, []))
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            return metrics

    def get_all_metrics(self) -> Dict[str, List[MetricPoint]]:
        """获取所有指标数据"""
        with self.lock:
            return {name: list(points) for name, points in self.metrics.items()}


class FileCollector(MetricCollector):
    """文件指标收集器"""

    def __init__(self, file_path: Path, flush_interval: int = 60):
        self.file_path = file_path
        self.flush_interval = flush_interval
        self.buffer: List[MetricPoint] = []
        self.lock = threading.Lock()
        self.last_flush = time.time()

        # 确保目录存在
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def collect(self, metric: MetricPoint):
        with self.lock:
            self.buffer.append(metric)

            # 自动刷新
            if time.time() - self.last_flush > self.flush_interval:
                self._flush_buffer()

    def flush(self):
        with self.lock:
            self._flush_buffer()

    def _flush_buffer(self):
        """刷新缓冲区到文件"""
        if not self.buffer:
            return

        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                for metric in self.buffer:
                    data = {
                        'name': metric.name,
                        'value': metric.value,
                        'timestamp': metric.timestamp,
                        'labels': metric.labels,
                        'type': metric.metric_type.value
                    }
                    f.write(json.dumps(data) + '\n')

            logger.debug(f"Flushed {len(self.buffer)} metrics to {self.file_path}")
            self.buffer.clear()
            self.last_flush = time.time()

        except Exception as e:
            logger.error(f"Failed to flush metrics to file: {e}")


class MetricsRegistry:
    """指标注册表"""

    def __init__(self):
        self.collectors: List[MetricCollector] = []
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()

    def add_collector(self, collector: MetricCollector):
        """添加指标收集器"""
        self.collectors.append(collector)

    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """记录计数器指标"""
        with self.lock:
            self.counters[name] += value

        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
            metric_type=MetricType.COUNTER
        )
        self._emit_metric(metric)

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录仪表盘指标"""
        with self.lock:
            self.gauges[name] = value

        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
            metric_type=MetricType.GAUGE
        )
        self._emit_metric(metric)

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录直方图指标"""
        with self.lock:
            self.histograms[name].append(value)

        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
            metric_type=MetricType.HISTOGRAM
        )
        self._emit_metric(metric)

    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """计时器上下文管理器"""
        return TimerContext(self, name, labels)

    def _emit_metric(self, metric: MetricPoint):
        """发送指标到所有收集器"""
        for collector in self.collectors:
            try:
                collector.collect(metric)
            except Exception as e:
                logger.error(f"Failed to collect metric {metric.name}: {e}")

    def flush_all(self):
        """刷新所有收集器"""
        for collector in self.collectors:
            try:
                collector.flush()
            except Exception as e:
                logger.error(f"Failed to flush collector: {e}")


class TimerContext:
    """计时器上下文管理器"""

    def __init__(self, registry: MetricsRegistry, name: str, labels: Optional[Dict[str, str]] = None):
        self.registry = registry
        self.name = name
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.registry.histogram(f"{self.name}_duration", duration, self.labels)

            # 记录成功/失败
            success = exc_type is None
            self.registry.counter(
                f"{self.name}_total",
                labels={**self.labels, "status": "success" if success else "error"}
            )


class MoningMetrics:
    """Moning 项目专用指标系统"""

    def __init__(self, output_dir: Path):
        self.registry = MetricsRegistry()
        self.output_dir = output_dir

        # 添加收集器
        self.memory_collector = InMemoryCollector()
        self.file_collector = FileCollector(output_dir / "metrics.jsonl")

        self.registry.add_collector(self.memory_collector)
        self.registry.add_collector(self.file_collector)

        # 性能指标缓存
        self.performance_metrics: List[PerformanceMetrics] = []
        self.business_metrics: List[BusinessMetrics] = []

    # API 调用指标
    def record_api_call(self, api_name: str, success: bool, duration: float, status_code: Optional[int] = None):
        """记录 API 调用指标"""
        labels = {
            "api": api_name,
            "status": "success" if success else "error"
        }
        if status_code:
            labels["status_code"] = str(status_code)

        self.registry.counter("api_calls_total", labels=labels)
        self.registry.histogram("api_call_duration", duration, labels=labels)

        if not success:
            self.registry.counter("api_errors_total", labels={"api": api_name})

    # 内容生成指标
    def record_content_generation(self, generator: str, success: bool, duration: float, source: str):
        """记录内容生成指标"""
        labels = {
            "generator": generator,
            "source": source,
            "status": "success" if success else "error"
        }

        self.registry.counter("content_generation_total", labels=labels)
        self.registry.histogram("content_generation_duration", duration, labels=labels)

        if success:
            self.registry.counter("content_generation_success_total", labels={"generator": generator})
        else:
            self.registry.counter("content_generation_errors_total", labels={"generator": generator})

    # 发布指标
    def record_publishing(self, platform: str, success: bool, duration: float):
        """记录发布指标"""
        labels = {
            "platform": platform,
            "status": "success" if success else "error"
        }

        self.registry.counter("publishing_total", labels=labels)
        self.registry.histogram("publishing_duration", duration, labels=labels)

    # 降级策略指标
    def record_fallback_usage(self, component: str, fallback_level: int):
        """记录降级策略使用"""
        labels = {
            "component": component,
            "level": str(fallback_level)
        }

        self.registry.counter("fallback_usage_total", labels=labels)

    # 错误指标
    def record_error(self, component: str, error_type: str, severity: str):
        """记录错误指标"""
        labels = {
            "component": component,
            "error_type": error_type,
            "severity": severity
        }

        self.registry.counter("errors_total", labels=labels)

    # 业务指标
    def record_daily_checkin(self, success: bool):
        """记录每日打卡"""
        status = "success" if success else "failed"
        self.registry.counter("daily_checkin_total", labels={"status": status})

        # 记录业务指标
        business_metric = BusinessMetrics(
            event="daily_checkin",
            count=1,
            timestamp=time.time(),
            properties={"success": success}
        )
        self.business_metrics.append(business_metric)

    def record_word_learning(self, word: str, success: bool):
        """记录单词学习"""
        status = "success" if success else "failed"
        self.registry.counter("word_learning_total", labels={"status": status})

        business_metric = BusinessMetrics(
            event="word_learning",
            count=1,
            timestamp=time.time(),
            properties={"word": word, "success": success}
        )
        self.business_metrics.append(business_metric)

    # 系统指标
    def record_system_health(self):
        """记录系统健康指标"""
        import psutil
        import os

        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent()
            self.registry.gauge("system_cpu_percent", cpu_percent)

            # 内存使用
            memory = psutil.virtual_memory()
            self.registry.gauge("system_memory_percent", memory.percent)
            self.registry.gauge("system_memory_used_bytes", memory.used)

            # 磁盘使用
            disk = psutil.disk_usage('/')
            self.registry.gauge("system_disk_percent", disk.percent)

            # 进程信息
            process = psutil.Process(os.getpid())
            self.registry.gauge("process_memory_bytes", process.memory_info().rss)
            self.registry.gauge("process_cpu_percent", process.cpu_percent())

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    # 获取统计信息
    def get_api_success_rate(self, api_name: str, time_window: int = 3600) -> float:
        """获取 API 成功率"""
        since = time.time() - time_window

        success_metrics = self.memory_collector.get_metrics("api_calls_total", since)
        success_count = sum(
            m.value for m in success_metrics
            if m.labels.get("api") == api_name and m.labels.get("status") == "success"
        )

        total_count = sum(
            m.value for m in success_metrics
            if m.labels.get("api") == api_name
        )

        return (success_count / total_count * 100) if total_count > 0 else 0.0

    def get_average_response_time(self, operation: str, time_window: int = 3600) -> float:
        """获取平均响应时间"""
        since = time.time() - time_window
        duration_metrics = self.memory_collector.get_metrics(f"{operation}_duration", since)

        if not duration_metrics:
            return 0.0

        total_duration = sum(m.value for m in duration_metrics)
        return total_duration / len(duration_metrics)

    def get_error_rate(self, component: str, time_window: int = 3600) -> float:
        """获取错误率"""
        since = time.time() - time_window

        error_metrics = self.memory_collector.get_metrics("errors_total", since)
        error_count = sum(
            m.value for m in error_metrics
            if m.labels.get("component") == component
        )

        # 假设每个错误对应一次操作尝试
        return error_count

    def generate_health_report(self) -> Dict[str, Any]:
        """生成健康报告"""
        report = {
            "timestamp": time.time(),
            "api_health": {},
            "content_generation": {},
            "publishing": {},
            "system": {},
            "business": {}
        }

        # API 健康状况
        for api in ["grok", "unsplash", "openai", "github", "telegram"]:
            report["api_health"][api] = {
                "success_rate": self.get_api_success_rate(api),
                "avg_response_time": self.get_average_response_time(f"api_{api}")
            }

        # 内容生成健康状况
        for generator in ["grok", "unsplash", "static"]:
            success_rate = self.get_api_success_rate(f"content_{generator}")
            report["content_generation"][generator] = {
                "success_rate": success_rate,
                "avg_duration": self.get_average_response_time(f"content_generation")
            }

        # 发布健康状况
        for platform in ["github", "telegram"]:
            report["publishing"][platform] = {
                "success_rate": self.get_api_success_rate(f"publish_{platform}"),
                "avg_duration": self.get_average_response_time(f"publishing")
            }

        # 系统健康状况
        system_metrics = self.memory_collector.get_metrics("system_cpu_percent")
        if system_metrics:
            latest_cpu = system_metrics[-1].value
            report["system"]["cpu_percent"] = latest_cpu

        memory_metrics = self.memory_collector.get_metrics("system_memory_percent")
        if memory_metrics:
            latest_memory = memory_metrics[-1].value
            report["system"]["memory_percent"] = latest_memory

        # 业务指标
        recent_checkins = [m for m in self.business_metrics if m.event == "daily_checkin" and m.timestamp > time.time() - 86400]
        report["business"]["daily_checkins"] = len(recent_checkins)

        recent_words = [m for m in self.business_metrics if m.event == "word_learning" and m.timestamp > time.time() - 86400]
        report["business"]["words_learned"] = len(recent_words)

        return report

    def flush(self):
        """刷新所有指标"""
        self.registry.flush_all()


# 全局指标实例
metrics: Optional[MoningMetrics] = None


def init_metrics(output_dir: Path):
    """初始化指标系统"""
    global metrics
    metrics = MoningMetrics(output_dir)
    logger.info(f"Metrics system initialized with output dir: {output_dir}")


def get_metrics() -> Optional[MoningMetrics]:
    """获取指标实例"""
    return metrics


# 装饰器：自动记录函数执行指标
def track_performance(component: str, operation: str):
    """性能追踪装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not metrics:
                return func(*args, **kwargs)

            start_time = time.time()
            success = False
            error = None

            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration = time.time() - start_time

                # 记录性能指标
                performance_metric = PerformanceMetrics(
                    operation=operation,
                    duration=duration,
                    success=success,
                    timestamp=start_time,
                    component=component,
                    metadata={"error": str(error) if error else None}
                )
                metrics.performance_metrics.append(performance_metric)

                # 记录到指标系统
                labels = {
                    "component": component,
                    "operation": operation,
                    "status": "success" if success else "error"
                }
                metrics.registry.histogram(f"{component}_duration", duration, labels)
                metrics.registry.counter(f"{component}_operations_total", labels=labels)

        return wrapper
    return decorator