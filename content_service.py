"""
内容生成服务模块
提供统一的多模态内容生成接口，支持优雅降级策略
"""

import logging
import random
import time
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import requests
from openai import OpenAI

from config import MoningConfig, POETRY_KEYWORD_MAPPING

logger = logging.getLogger(__name__)


@dataclass
class ContentRequest:
    """内容生成请求"""
    sentence: str
    theme: Optional[str] = None
    style: Optional[str] = None
    size: str = "1024x1024"


@dataclass
class GeneratedContent:
    """生成的内容结果"""
    image_url: Optional[str] = None
    image_path: Optional[Path] = None
    source: str = "unknown"  # "ai_generated", "api_matched", "static_fallback"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContentGenerator(ABC):
    """内容生成器抽象基类"""

    def __init__(self, config: MoningConfig):
        self.config = config

    @abstractmethod
    def generate(self, request: ContentRequest) -> Optional[GeneratedContent]:
        """生成内容"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查生成器是否可用"""
        pass


class GeminiImagenGenerator(ContentGenerator):
    """Gemini Imagen 图片生成器"""

    def __init__(self, config: MoningConfig):
        super().__init__(config)
        self.client = None
        if config.gemini_imagen.api_key:
            self.client = OpenAI(
                api_key=config.gemini_imagen.api_key,
                base_url=config.gemini_imagen.base_url
            )

    def is_available(self) -> bool:
        return self.client is not None and self.config.gemini_imagen.api_key is not None

    def generate(self, request: ContentRequest) -> Optional[GeneratedContent]:
        if not self.is_available():
            logger.warning("Gemini Imagen generator not available")
            return None

        try:
            # 分析诗词主题
            theme, elements = self._analyze_poetry_theme(request.sentence)

            # 构建提示词
            prompt = self._build_image_prompt(request.sentence, theme, elements)

            # 生成图片
            for attempt in range(self.config.app.max_retry_attempts):
                try:
                    logger.info(f"Gemini Imagen image generation attempt {attempt + 1}")

                    # 优先使用 images 接口
                    try:
                        response = self.client.images.generate(
                            model=self.config.gemini_imagen.model,
                            prompt=prompt,
                            size=request.size,
                            quality="standard",
                            n=1
                        )

                        if response.data and len(response.data) > 0:
                            image_url = response.data[0].url
                            if image_url:
                                # 下载并保存图片
                                image_path = self._download_image(image_url, "gemini_imagen")

                                logger.info(f"Successfully generated Gemini Imagen image on attempt {attempt + 1}")
                                return GeneratedContent(
                                    image_url=image_url,
                                    image_path=image_path,
                                    source="ai_generated",
                                    metadata={
                                        "generator": "gemini_imagen",
                                        "theme": theme,
                                        "elements": elements,
                                        "prompt": prompt,
                                        "attempt": attempt + 1,
                                        "method": "images_api"
                                    }
                                )

                        logger.warning("Gemini Imagen images API returned no usable URL, fallback to chat API")

                    except Exception as images_error:
                        logger.warning(f"Gemini Imagen images API failed, fallback to chat API: {images_error}")

                    # 回退到 chat 接口
                    chat_response = self.client.chat.completions.create(
                        model=self.config.gemini_imagen.model,
                        messages=[
                            {
                                "role": "user",
                                "content": f"Generate an image: {prompt}"
                            }
                        ],
                        max_tokens=500
                    )

                    if chat_response.choices and len(chat_response.choices) > 0:
                        response_text = chat_response.choices[0].message.content
                        logger.info(f"Gemini Imagen chat response: {response_text}")

                        # 从响应中提取图片URL
                        import re
                        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                        urls = re.findall(url_pattern, response_text)

                        for url in urls:
                            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                # 下载并保存图片
                                image_path = self._download_image(url, "gemini_imagen")

                                logger.info(f"Successfully extracted image URL from Gemini Imagen chat: {url}")
                                return GeneratedContent(
                                    image_url=url,
                                    image_path=image_path,
                                    source="ai_generated",
                                    metadata={
                                        "generator": "gemini_imagen",
                                        "theme": theme,
                                        "elements": elements,
                                        "prompt": prompt,
                                        "attempt": attempt + 1,
                                        "method": "chat_api"
                                    }
                                )

                        logger.warning("No valid image URL found in Gemini Imagen chat response")

                    logger.warning(f"Gemini Imagen image generation returned no result (attempt {attempt + 1})")

                except Exception as e:
                    logger.error(f"Gemini Imagen image generation failed on attempt {attempt + 1}: {e}")
                    if attempt < self.config.app.max_retry_attempts - 1:
                        delay = self.config.app.retry_delay_base ** attempt
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)

            logger.error("All Gemini Imagen image generation attempts failed")
            return None

        except Exception as e:
            logger.error(f"Gemini Imagen image generation error: {e}")
            return None

    def _analyze_poetry_theme(self, sentence: str) -> Tuple[str, Dict[str, List[str]]]:
        """分析诗词主题"""
        try:
            # 使用 OpenAI 客户端进行主题分析
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # 使用通用模型进行分析
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个中国古典诗词分析专家。请分析给定诗句的主题和意境，提取关键元素。"
                    },
                    {
                        "role": "user",
                        "content": f"请分析这句诗的主题和关键元素：{sentence}\n\n请用以下格式回答：\n主题：[主题名称]\n元素：[元素1,元素2,元素3]"
                    }
                ],
                max_tokens=200,
                temperature=0.7
            )

            content = response.choices[0].message.content
            lines = content.strip().split('\n')

            theme = "自然风光"
            elements = ["mountain", "water", "sky"]

            for line in lines:
                if line.startswith("主题："):
                    theme = line.replace("主题：", "").strip()
                elif line.startswith("元素："):
                    element_str = line.replace("元素：", "").strip()
                    elements = [e.strip() for e in element_str.split(',')]

            return theme, {"elements": elements}

        except Exception as e:
            logger.error(f"Failed to analyze poetry theme: {e}")
            return "自然风光", {"elements": ["mountain", "water", "sky"]}

    def _build_image_prompt(self, sentence: str, theme: str, elements: Dict[str, List[str]]) -> str:
        """构建图片生成提示词"""
        base_elements = elements.get("elements", ["landscape"])

        prompt = f"""Create a beautiful, serene landscape image inspired by Chinese classical poetry.

Theme: {theme}
Key elements: {', '.join(base_elements)}
Poetry: {sentence}

Style: Traditional Chinese landscape painting aesthetic, soft lighting, peaceful atmosphere, high quality, artistic composition.
Avoid: text, characters, people, modern elements."""

        return prompt

    def _download_image(self, url: str, prefix: str) -> Optional[Path]:
        """下载图片到本地"""
        try:
            import pendulum

            # 创建输出目录
            today = pendulum.now(self.config.app.timezone).format("YYYY-MM-DD")
            output_dir = self.config.app.output_dir / today
            output_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = int(time.time())
            filename = f"{prefix}_{timestamp}_0.jpg"
            filepath = output_dir / filename

            # 下载图片
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Image downloaded to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None


class UnsplashImageGenerator(ContentGenerator):
    """Unsplash 图片匹配器"""

    def is_available(self) -> bool:
        return self.config.unsplash.api_key is not None

    def generate(self, request: ContentRequest) -> Optional[GeneratedContent]:
        if not self.is_available():
            logger.warning("Unsplash generator not available")
            return None

        try:
            # 提取关键词
            keywords = self._extract_keywords(request.sentence)

            # 搜索图片
            for keyword_set in keywords:
                query = " ".join(keyword_set)
                image_url = self._search_unsplash(query)

                if image_url:
                    # 下载图片
                    image_path = self._download_image(image_url, "unsplash")

                    return GeneratedContent(
                        image_url=image_url,
                        image_path=image_path,
                        source="api_matched",
                        metadata={
                            "generator": "unsplash",
                            "query": query,
                            "keywords": keyword_set
                        }
                    )

            logger.warning("No suitable Unsplash images found")
            return None

        except Exception as e:
            logger.error(f"Unsplash image search error: {e}")
            return None

    def _extract_keywords(self, sentence: str) -> List[List[str]]:
        """从诗句中提取关键词"""
        keyword_sets = []

        # 基于字符匹配
        for char in sentence:
            if char in POETRY_KEYWORD_MAPPING:
                keyword_sets.append(POETRY_KEYWORD_MAPPING[char])

        # 如果没有匹配到关键词，使用默认关键词
        if not keyword_sets:
            keyword_sets.append(POETRY_KEYWORD_MAPPING["default"])

        return keyword_sets

    def _search_unsplash(self, query: str) -> Optional[str]:
        """搜索 Unsplash 图片"""
        try:
            headers = {"Authorization": f"Client-ID {self.config.unsplash.api_key}"}
            params = {
                "query": query,
                "per_page": 10,
                "orientation": "landscape"
            }

            response = requests.get(
                self.config.unsplash.search_endpoint,
                headers=headers,
                params=params,
                timeout=self.config.unsplash.timeout
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if results:
                    # 随机选择一张图片
                    photo = random.choice(results)
                    return photo["urls"]["regular"]

            logger.warning(f"Unsplash search failed: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Unsplash search error: {e}")
            return None

    def _download_image(self, url: str, prefix: str) -> Optional[Path]:
        """下载图片到本地"""
        try:
            import pendulum

            # 创建输出目录
            today = pendulum.now(self.config.app.timezone).format("YYYY-MM-DD")
            output_dir = self.config.app.output_dir / today
            output_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = int(time.time())
            filename = f"{prefix}_{timestamp}_0.jpg"
            filepath = output_dir / filename

            # 下载图片
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Image downloaded to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None


class StaticImageGenerator(ContentGenerator):
    """静态图片备选器"""

    def is_available(self) -> bool:
        return len(self.config.app.static_fallback_images) > 0

    def generate(self, request: ContentRequest) -> Optional[GeneratedContent]:
        if not self.is_available():
            logger.warning("Static generator not available")
            return None

        try:
            # 随机选择一张静态图片
            image_url = random.choice(self.config.app.static_fallback_images)

            # 下载图片
            image_path = self._download_image(image_url, "static")

            return GeneratedContent(
                image_url=image_url,
                image_path=image_path,
                source="static_fallback",
                metadata={
                    "generator": "static",
                    "fallback": True
                }
            )

        except Exception as e:
            logger.error(f"Static image generation error: {e}")
            return None

    def _download_image(self, url: str, prefix: str) -> Optional[Path]:
        """下载图片到本地"""
        try:
            import pendulum

            # 创建输出目录
            today = pendulum.now(self.config.app.timezone).format("YYYY-MM-DD")
            output_dir = self.config.app.output_dir / today
            output_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = int(time.time())
            filename = f"{prefix}_{timestamp}_0.jpg"
            filepath = output_dir / filename

            # 下载图片
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Image downloaded to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None


class ContentGenerationService:
    """内容生成服务 - 实现优雅降级策略"""

    def __init__(self, config: MoningConfig):
        self.config = config
        self.generators = [
            GeminiImagenGenerator(config),
            UnsplashImageGenerator(config),
            StaticImageGenerator(config)
        ]

    def generate_content(self, request: ContentRequest) -> Optional[GeneratedContent]:
        """生成内容，按优先级尝试各个生成器"""
        logger.info(f"Starting content generation for: {request.sentence[:50]}...")

        for i, generator in enumerate(self.generators):
            generator_name = generator.__class__.__name__

            if not generator.is_available():
                logger.info(f"{generator_name} is not available, skipping")
                continue

            logger.info(f"Trying {generator_name} (priority {i+1})")

            try:
                content = generator.generate(request)
                if content:
                    logger.info(f"Successfully generated content using {generator_name}")
                    return content
                else:
                    logger.warning(f"{generator_name} failed to generate content")

            except Exception as e:
                logger.error(f"{generator_name} error: {e}")

        logger.error("All content generators failed")
        return None

    def get_available_generators(self) -> List[str]:
        """获取可用的生成器列表"""
        return [
            generator.__class__.__name__
            for generator in self.generators
            if generator.is_available()
        ]


def get_sentence_from_api(api_url: str) -> str:
    """从 API 获取诗句"""
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            origin = data.get("origin", "")
            author = data.get("author", "")

            if content:
                # 格式化诗句
                if origin and author:
                    return f"{content}\r\n——{author}《{origin}》"
                else:
                    return content

        logger.warning(f"Failed to get sentence from API: {response.status_code}")
        return ""

    except Exception as e:
        logger.error(f"Failed to get sentence from API: {e}")
        return ""