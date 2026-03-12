"""
Moning 项目统一配置管理模块
提供类型安全的配置管理和环境变量处理
"""

import os
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path


def _normalize_openai_base_url(base_url: Optional[str], default: str) -> str:
    """Normalize OpenAI-compatible base URLs to include the /v1 suffix."""
    value = (base_url or default).rstrip("/")
    if value.endswith("/v1"):
        return value
    return f"{value}/v1"


@dataclass
class APIConfig:
    """API 配置基类"""
    base_url: str
    api_key: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3


@dataclass
class GeminiImagenConfig(APIConfig):
    """Gemini Imagen API 配置"""
    model: str = "gemini-imagen"

    @classmethod
    def from_env(cls) -> 'GeminiImagenConfig':
        default_base_url = "https://ai.huan666.de/v1"
        model = os.environ.get("GEMINI_IMAGEN_MODEL", "gemini-imagen")
        if not model:
            model = "gemini-imagen"
        return cls(
            base_url=_normalize_openai_base_url(
                os.environ.get("GEMINI_IMAGEN_API_BASE"),
                default_base_url
            ),
            api_key=os.environ.get("GEMINI_IMAGEN_API_KEY"),
            model=model,
            timeout=int(os.environ.get("GEMINI_IMAGEN_TIMEOUT", "60")),
            max_retries=int(os.environ.get("GEMINI_IMAGEN_MAX_RETRIES", "3"))
        )


@dataclass
class UnsplashConfig(APIConfig):
    """Unsplash API 配置"""
    search_endpoint: str = "/search/photos"

    @classmethod
    def from_env(cls) -> 'UnsplashConfig':
        base_url = "https://api.unsplash.com"
        return cls(
            base_url=base_url,
            api_key=os.environ.get("UNSPLASH_ACCESS_KEY"),
            search_endpoint=f"{base_url}/search/photos",
            timeout=int(os.environ.get("UNSPLASH_TIMEOUT", "30")),
            max_retries=int(os.environ.get("UNSPLASH_MAX_RETRIES", "3"))
        )


@dataclass
class OpenAIConfig(APIConfig):
    """OpenAI API 配置"""
    model: str = "gpt-4"

    @classmethod
    def from_env(cls) -> 'OpenAIConfig':
        model = os.environ.get("OPENAI_MODEL", "gpt-4")
        if not model:
            model = "gpt-4"
        return cls(
            base_url=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
            api_key=os.environ.get("OPENAI_API_KEY"),
            model=model,
            timeout=int(os.environ.get("OPENAI_TIMEOUT", "60")),
            max_retries=int(os.environ.get("OPENAI_MAX_RETRIES", "3"))
        )


@dataclass
class GitHubConfig:
    """GitHub 配置"""
    token: Optional[str] = None
    repo_name: Optional[str] = None
    issue_number: int = 1

    @classmethod
    def from_env(cls) -> 'GitHubConfig':
        return cls(
            token=os.environ.get("GITHUB_TOKEN"),
            repo_name=os.environ.get("GITHUB_REPO"),
            issue_number=int(os.environ.get("GET_UP_ISSUE_NUMBER", "1"))
        )


@dataclass
class TelegramConfig:
    """Telegram 配置"""
    token: Optional[str] = None
    chat_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'TelegramConfig':
        return cls(
            token=os.environ.get("TELEGRAM_TOKEN"),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID")
        )


@dataclass
class AppConfig:
    """应用主配置"""
    timezone: str = "Asia/Shanghai"
    output_dir: Path = Path("OUT_DIR")
    sentence_api: str = "https://v1.jinrishici.com/all"
    default_sentence: str = "赏花归去马如飞\r\n去马如飞酒力微\r\n酒力微醒时已暮\r\n醒时已暮赏花归\r\n"

    # 图片生成配置
    image_generation_timeout: int = 60
    max_retry_attempts: int = 3
    retry_delay_base: int = 2

    # 静态备选图片
    static_fallback_images: List[str] = None

    def __post_init__(self):
        if self.static_fallback_images is None:
            self.static_fallback_images = [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",  # 日出
                "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800",  # 森林
                "https://images.unsplash.com/photo-1464822759844-d150baec5b1b?w=800",  # 山景
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",  # 湖泊
            ]

    @classmethod
    def from_env(cls) -> 'AppConfig':
        return cls(
            timezone=os.environ.get("TIMEZONE", "Asia/Shanghai"),
            output_dir=Path(os.environ.get("OUTPUT_DIR", "OUT_DIR")),
            sentence_api=os.environ.get("SENTENCE_API", "https://v1.jinrishici.com/all"),
            image_generation_timeout=int(os.environ.get("IMAGE_GENERATION_TIMEOUT", "60")),
            max_retry_attempts=int(os.environ.get("MAX_RETRY_ATTEMPTS", "3")),
            retry_delay_base=int(os.environ.get("RETRY_DELAY_BASE", "2"))
        )


@dataclass
class MoningConfig:
    """Moning 项目完整配置"""
    app: AppConfig
    gemini_imagen: GeminiImagenConfig
    unsplash: UnsplashConfig
    openai: OpenAIConfig
    github: GitHubConfig
    telegram: TelegramConfig

    @classmethod
    def from_env(cls) -> 'MoningConfig':
        """从环境变量创建完整配置"""
        return cls(
            app=AppConfig.from_env(),
            gemini_imagen=GeminiImagenConfig.from_env(),
            unsplash=UnsplashConfig.from_env(),
            openai=OpenAIConfig.from_env(),
            github=GitHubConfig.from_env(),
            telegram=TelegramConfig.from_env()
        )

    def validate(self) -> List[str]:
        """验证配置完整性，返回错误列表"""
        errors = []

        # 检查必需的 API 密钥
        if not self.gemini_imagen.api_key:
            errors.append("GEMINI_IMAGEN_API_KEY is required")

        if not self.unsplash.api_key:
            errors.append("UNSPLASH_ACCESS_KEY is required")

        if not self.github.token:
            errors.append("GITHUB_TOKEN is required")

        if not self.github.repo_name:
            errors.append("GITHUB_REPO is required")

        # Telegram 配置是可选的，但如果提供了 token 就需要 chat_id
        if self.telegram.token and not self.telegram.chat_id:
            errors.append("TELEGRAM_CHAT_ID is required when TELEGRAM_TOKEN is provided")

        # 检查输出目录
        if not self.app.output_dir.exists():
            try:
                self.app.output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create output directory {self.app.output_dir}: {e}")

        return errors


def load_config(strict: bool = True) -> MoningConfig:
    """加载并验证配置

    Args:
        strict: 是否严格验证，False 时允许缺少必需的配置项
    """
    config = MoningConfig.from_env()

    if strict:
        errors = config.validate()
        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"- {error}" for error in errors))

    return config


# 诗词到 Unsplash 关键词映射
POETRY_KEYWORD_MAPPING = {
    # 自然元素
    "山": ["mountain", "peak", "hill"],
    "水": ["water", "river", "lake"],
    "云": ["cloud", "sky", "weather"],
    "雨": ["rain", "storm", "weather"],
    "雪": ["snow", "winter", "white"],
    "风": ["wind", "breeze", "nature"],
    "花": ["flower", "blossom", "spring"],
    "树": ["tree", "forest", "nature"],
    "月": ["moon", "night", "lunar"],
    "日": ["sun", "sunrise", "sunset"],
    "星": ["star", "night", "sky"],

    # 季节和时间
    "春": ["spring", "bloom", "green"],
    "夏": ["summer", "warm", "bright"],
    "秋": ["autumn", "fall", "golden"],
    "冬": ["winter", "cold", "snow"],
    "晨": ["morning", "dawn", "sunrise"],
    "夜": ["night", "dark", "moon"],
    "黄昏": ["sunset", "dusk", "evening"],

    # 情感和意境
    "静": ["peaceful", "calm", "serene"],
    "美": ["beautiful", "aesthetic", "elegant"],
    "远": ["distant", "horizon", "landscape"],
    "高": ["high", "tall", "elevated"],
    "深": ["deep", "profound", "mysterious"],
    "清": ["clear", "pure", "clean"],
    "幽": ["quiet", "secluded", "tranquil"],

    # 建筑和人文
    "楼": ["building", "architecture", "tower"],
    "桥": ["bridge", "connection", "architecture"],
    "路": ["road", "path", "journey"],
    "城": ["city", "urban", "architecture"],
    "村": ["village", "rural", "countryside"],
    "寺": ["temple", "spiritual", "architecture"],

    # 动物
    "鸟": ["bird", "flying", "nature"],
    "鱼": ["fish", "water", "ocean"],
    "马": ["horse", "animal", "freedom"],
    "燕": ["swallow", "bird", "spring"],

    # 植物
    "竹": ["bamboo", "green", "zen"],
    "松": ["pine", "evergreen", "mountain"],
    "梅": ["plum", "winter", "blossom"],
    "荷": ["lotus", "water", "summer"],
    "菊": ["chrysanthemum", "autumn", "flower"],

    # 默认关键词
    "default": ["landscape", "nature", "peaceful", "beautiful"]
}
