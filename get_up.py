import argparse
import os
from pathlib import Path
import random
import logging
import time
from typing import List, Optional, Tuple

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import pendulum
import requests
import telebot
from telebot.types import InputMediaPhoto
from github import Github
from openai import OpenAI

# Constants
GET_UP_ISSUE_NUMBER = 1
GET_UP_MESSAGE_TEMPLATE = "#Now 记录时间是--{get_up_time}.\r\n\r\n今天的一句诗:\r\n{sentence}\r\n\r\n📅 年度进度:\r\n{year_progress}\r\n"
SENTENCE_API = "https://v1.jinrishici.com/all"
DEFAULT_SENTENCE = "赏花归去马如飞\r\n去马如飞酒力微\r\n酒力微醒时已暮\r\n醒时已暮赏花归\r\n"
TIMEZONE = "Asia/Shanghai"
IMAGE_OUTPUT_DIR = Path("OUT_DIR")

# Image generation constants
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_BASE = 2  # seconds
IMAGE_GENERATION_TIMEOUT = 60  # seconds

# Unsplash API configuration
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
UNSPLASH_API_BASE = "https://api.unsplash.com"
UNSPLASH_SEARCH_ENDPOINT = f"{UNSPLASH_API_BASE}/search/photos"

# Static fallback images (used when Unsplash API fails)
STATIC_FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",  # 日出
    "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800",  # 森林
    "https://images.unsplash.com/photo-1464822759844-d150baec5b1b?w=800",  # 山景
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800",  # 湖泊
]

# Poetry to Unsplash keywords mapping
POETRY_KEYWORDS_MAPPING = {
    "nature": ["landscape", "nature", "mountain", "forest", "river", "lake", "sky"],
    "season": ["spring", "summer", "autumn", "winter", "seasonal", "bloom", "snow"],
    "emotion": ["peaceful", "serene", "calm", "tranquil", "meditation", "zen"],
    "default": ["beautiful", "scenic", "artistic", "poetic", "landscape", "nature"]
}

# Poetry prompt templates
POETRY_PROMPT_TEMPLATES = {
    "nature": "Create a beautiful, serene landscape image inspired by Chinese poetry. Style: traditional Chinese ink painting meets modern digital art. Elements: {elements}. Mood: peaceful, contemplative, ethereal. Colors: soft pastels with traditional Chinese color palette. Quality: high resolution, detailed, artistic.",
    "season": "Generate a seasonal scene that captures the essence of Chinese poetry. Season: {season}. Style: blend of traditional Chinese art and contemporary digital painting. Atmosphere: poetic, dreamy, nostalgic. Details: {details}. Color scheme: harmonious and natural.",
    "emotion": "Create an emotional landscape that reflects the mood of Chinese poetry. Emotion: {emotion}. Style: artistic, impressionistic with Chinese aesthetic elements. Composition: balanced, flowing. Lighting: soft, atmospheric. Colors: muted tones with emotional depth.",
    "default": "Generate a beautiful, artistic image inspired by Chinese poetry and traditional aesthetics. Style: modern digital art with traditional Chinese painting elements. Mood: serene, contemplative, poetic. Quality: high resolution, detailed, visually stunning."
}

# OpenAI client setup
if api_base := os.environ.get("OPENAI_API_BASE"):
    client = OpenAI(base_url=api_base, api_key=os.environ.get("OPENAI_API_KEY"))
else:
    client = OpenAI()

# FastGPT API configuration
FASTGPT_API_KEY = os.environ.get("FASTGPT_API_KEY", "fastgpt-xwRC0Ea1FFFFGR0xJZjhz0zTyGXuwJdbzhDt31igWvyYsLkWf1qZzhjXICt5")
FASTGPT_API_BASE = "https://api.fastgpt.in/api/v1/chat/completions#"
FASTGPT_MODEL = "FLUX.1 DEV"  # 使用FLUX.1 DEV模型生成图片

# FastGPT client setup
if FASTGPT_API_KEY:
    fastgpt_client = OpenAI(
        base_url=FASTGPT_API_BASE,
        api_key=FASTGPT_API_KEY
    )
else:
    fastgpt_client = None
    logger.warning("FASTGPT_API_KEY not configured")

def get_all_til_knowledge_file():
    til_dir = Path(os.environ.get("MORNING_REPO_NAME"))
    today_dir = random.choice(list(til_dir.iterdir()))
    md_files = []
    for root, _, files in os.walk(today_dir):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))
    return md_files

def login(token):
    return Github(token)

def get_one_sentence():
    try:
        r = requests.get(SENTENCE_API, timeout=10)
        if r.ok:
            return r.json()["content"]
        logger.warning(f"API returned status {r.status_code}")
        return DEFAULT_SENTENCE
    except requests.RequestException as e:
        logger.error(f"Failed to get sentence from API: {e}")
        return DEFAULT_SENTENCE
    except Exception as e:
        logger.error(f"Unexpected error getting sentence: {e}")
        return DEFAULT_SENTENCE

def analyze_poetry_theme(sentence: str) -> Tuple[str, dict]:
    """
    分析诗词主题，返回主题类型和相关参数
    """
    try:
        analysis_prompt = f"""
        分析以下中文诗词的主题和元素，返回JSON格式：
        诗词：{sentence}
        
        请分析并返回以下信息：
        1. theme: 主题类型 (nature/season/emotion/default)
        2. elements: 主要元素列表
        3. season: 季节 (如果是季节主题)
        4. emotion: 情感 (如果是情感主题)
        5. details: 具体细节描述
        
        只返回JSON，不要其他文字。
        """
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": analysis_prompt}],
            model="gpt-4o-mini",
            temperature=0.3
        )
        
        result = completion.choices[0].message.content.strip()
        # 尝试解析JSON
        import json
        analysis = json.loads(result)
        return analysis.get("theme", "default"), analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze poetry theme: {e}")
        return "default", {"elements": ["mountain", "water", "sky"], "details": "serene landscape"}

def generate_enhanced_prompt(sentence: str) -> str:
    """
    生成增强的图片提示词
    """
    try:
        theme, analysis = analyze_poetry_theme(sentence)
        template = POETRY_PROMPT_TEMPLATES.get(theme, POETRY_PROMPT_TEMPLATES["default"])
        
        # 根据主题填充模板
        if theme == "nature":
            elements = ", ".join(analysis.get("elements", ["mountain", "water", "trees"]))
            return template.format(elements=elements)
        elif theme == "season":
            season = analysis.get("season", "spring")
            details = analysis.get("details", "blooming flowers and gentle breeze")
            return template.format(season=season, details=details)
        elif theme == "emotion":
            emotion = analysis.get("emotion", "peaceful")
            return template.format(emotion=emotion)
        else:
            return template
            
    except Exception as e:
        logger.error(f"Failed to generate enhanced prompt: {e}")
        return POETRY_PROMPT_TEMPLATES["default"]

def get_unsplash_image_by_theme(theme: str, analysis: dict) -> Optional[str]:
    """
    根据诗词主题从Unsplash API获取相关图片
    """
    if not UNSPLASH_ACCESS_KEY:
        logger.warning("UNSPLASH_ACCESS_KEY not configured, using static fallback")
        return None
    
    try:
        # 根据主题选择关键词
        keywords = POETRY_KEYWORDS_MAPPING.get(theme, POETRY_KEYWORDS_MAPPING["default"])
        
        # 根据分析结果调整关键词
        if theme == "nature" and "elements" in analysis:
            elements = analysis["elements"]
            if isinstance(elements, list):
                # 将中文元素转换为英文关键词
                element_mapping = {
                    "山": "mountain", "水": "water", "树": "tree", "花": "flower",
                    "云": "cloud", "月": "moon", "日": "sun", "星": "star",
                    "鸟": "bird", "鱼": "fish", "竹": "bamboo", "松": "pine"
                }
                for element in elements:
                    if element in element_mapping:
                        keywords.append(element_mapping[element])
        
        # 随机选择一个关键词进行搜索
        search_keyword = random.choice(keywords)
        
        # 构建API请求
        headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
            "Accept-Version": "v1"
        }
        
        params = {
            "query": search_keyword,
            "per_page": 10,
            "orientation": "landscape",
            "order_by": "relevant"
        }
        
        logger.info(f"Searching Unsplash for keyword: {search_keyword}")
        
        response = requests.get(
            UNSPLASH_SEARCH_ENDPOINT,
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            if results:
                # 随机选择一张图片
                selected_image = random.choice(results)
                image_url = selected_image["urls"]["regular"]
                logger.info(f"Successfully fetched Unsplash image: {image_url}")
                return image_url
            else:
                logger.warning(f"No images found for keyword: {search_keyword}")
        else:
            logger.error(f"Unsplash API error: {response.status_code} - {response.text}")
            
    except requests.RequestException as e:
        logger.error(f"Failed to fetch from Unsplash API: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching Unsplash image: {e}")
    
    return None

def get_fallback_image(theme: str = "default", analysis: dict = None) -> str:
    """
    获取备选图片 - 优先使用Unsplash API，失败时使用静态图片
    """
    # 尝试从Unsplash API获取图片
    unsplash_image = get_unsplash_image_by_theme(theme, analysis or {})
    
    if unsplash_image:
        return unsplash_image
    
    # 如果Unsplash API失败，使用静态备选图片
    logger.info("Using static fallback image")
    return random.choice(STATIC_FALLBACK_IMAGES)

def get_year_progress():
    """获取今年的进度条"""
    now = pendulum.now(TIMEZONE)
    day_of_year = now.day_of_year

    # 判断是否为闰年
    is_leap_year = now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0)
    total_days = 366 if is_leap_year else 365

    # 计算进度百分比
    progress_percent = (day_of_year / total_days) * 100

    # 生成进度条 (20个字符宽度)
    progress_bar_width = 20
    filled_blocks = int((day_of_year / total_days) * progress_bar_width)
    empty_blocks = progress_bar_width - filled_blocks

    progress_bar = "█" * filled_blocks + "░" * empty_blocks

    return f"{progress_bar} {progress_percent:.1f}% ({day_of_year}/{total_days})"

def get_today_get_up_status(issue):
    comments = list(issue.get_comments())
    if not comments:
        return False
    latest_comment = comments[-1]
    now = pendulum.now(TIMEZONE)
    latest_day = pendulum.instance(latest_comment.created_at).in_timezone(TIMEZONE)
    is_today = (latest_day.day == now.day) and (latest_day.month == now.month)
    return is_today

def generate_image_with_fastgpt(prompt: str) -> Optional[str]:
    """
    使用FastGPT API和FLUX.1 DEV模型直接生成AI图片
    """
    if not fastgpt_client:
        logger.error("FastGPT client not configured")
        return None
    
    try:
        # 构建图片生成请求
        image_prompt = f"""
        Generate a beautiful, artistic image based on this Chinese poetry description: {prompt}
        
        The image should be:
        - High quality and visually appealing
        - Suitable for a morning poetry sharing context
        - Artistic and inspiring
        - In landscape orientation
        - Reflect the mood and theme of the poetry
        """
        
        logger.info(f"Generating image with FastGPT FLUX.1 DEV for prompt: {prompt}")
        
        response = fastgpt_client.chat.completions.create(
            model=FASTGPT_MODEL,
            messages=[{"role": "user", "content": image_prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        if response.choices and len(response.choices) > 0:
            # FastGPT返回的是文本响应，包含图片URL
            response_text = response.choices[0].message.content
            logger.info(f"FastGPT response: {response_text}")
            
            # 尝试从响应中提取图片URL
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(?:jpg|jpeg|png|gif|webp)'
            urls = re.findall(url_pattern, response_text)
            
            if urls:
                image_url = urls[0]
                logger.info(f"Successfully extracted image URL: {image_url}")
                return image_url
            else:
                logger.warning("No image URL found in FastGPT response")
                return None
        else:
            logger.warning("No response data returned from FastGPT")
            return None
            
    except Exception as e:
        logger.error(f"Failed to generate image with FastGPT: {e}")
        return None

def get_unsplash_image_by_keywords(keywords: List[str]) -> Optional[str]:
    """
    根据关键词从Unsplash获取图片
    """
    if not UNSPLASH_ACCESS_KEY:
        logger.warning("UNSPLASH_ACCESS_KEY not configured")
        return None
    
    try:
        # 随机选择一个关键词进行搜索
        search_keyword = random.choice(keywords)
        
        # 构建API请求
        headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
            "Accept-Version": "v1"
        }
        
        params = {
            "query": search_keyword,
            "per_page": 10,
            "orientation": "landscape",
            "order_by": "relevant"
        }
        
        logger.info(f"Searching Unsplash for keyword: {search_keyword}")
        
        response = requests.get(
            UNSPLASH_SEARCH_ENDPOINT,
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            if results:
                # 随机选择一张图片
                selected_image = random.choice(results)
                image_url = selected_image["urls"]["regular"]
                logger.info(f"Successfully fetched Unsplash image: {image_url}")
                return image_url
            else:
                logger.warning(f"No images found for keyword: {search_keyword}")
        else:
            logger.error(f"Unsplash API error: {response.status_code} - {response.text}")
            
    except requests.RequestException as e:
        logger.error(f"Failed to fetch from Unsplash API: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching Unsplash image: {e}")
    
    return None

def make_pic_and_save(sentence: str) -> Optional[List[str]]:
    """
    生成并保存图片，同时获取FastGPT AI图片和Unsplash备选图片
    """
    logger.info(f"Starting dual image generation for sentence: {sentence}")
    
    # 生成增强的提示词
    try:
        enhanced_prompt = generate_enhanced_prompt(sentence)
        logger.info(f"Generated enhanced prompt: {enhanced_prompt}")
    except Exception as e:
        logger.error(f"Failed to generate enhanced prompt: {e}")
        enhanced_prompt = sentence  # 使用原始诗词作为备选
    
    # 创建输出目录
    now = pendulum.now()
    date_str = now.to_date_string()
    new_path = IMAGE_OUTPUT_DIR / date_str
    new_path.mkdir(parents=True, exist_ok=True)
    
    images_list = []
    
    # 1. 尝试生成FastGPT AI图片
    fastgpt_image = None
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            logger.info(f"FastGPT image generation attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}")
            
            # 使用FastGPT FLUX.1 DEV模型直接生成AI图片
            fastgpt_image = generate_image_with_fastgpt(enhanced_prompt)
            
            if fastgpt_image:
                logger.info(f"Successfully generated FastGPT image on attempt {attempt + 1}")
                images_list.append(fastgpt_image)
                break
            else:
                logger.warning(f"FastGPT image generation returned no result (attempt {attempt + 1})")
                
        except Exception as e:
            logger.error(f"FastGPT image generation failed on attempt {attempt + 1}: {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)  # 指数退避
                logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
            else:
                logger.error("All FastGPT image generation attempts failed")
    
    # 2. 获取Unsplash备选图片
    try:
        logger.info("Getting Unsplash fallback image")
        theme, analysis = analyze_poetry_theme(sentence)
        unsplash_image = get_fallback_image(theme, analysis)
        
        if unsplash_image and unsplash_image not in images_list:
            logger.info("Successfully got Unsplash fallback image")
            images_list.append(unsplash_image)
        else:
            logger.warning("Failed to get Unsplash fallback image or duplicate")
            
    except Exception as e:
        logger.error(f"Failed to get Unsplash fallback image: {e}")
    
    # 3. 如果都没有，使用静态备选图片
    if not images_list:
        logger.info("Using static fallback images")
        static_image = random.choice(STATIC_FALLBACK_IMAGES)
        images_list.append(static_image)
    
    logger.info(f"Final result: {len(images_list)} images available")
    return images_list if images_list else None

def make_get_up_message() -> Tuple[str, bool, List[str], str]:
    """
    生成早起消息，包含图片生成和备选方案
    """
    sentence = get_one_sentence()
    now = pendulum.now(TIMEZONE)
    is_get_up_early = 0 <= now.hour <= 24
    images_list = []
    theme = "default"
    analysis = {}
    
    logger.info(f"Generating wake-up message for sentence: {sentence}")
    
    # 获取年度进度
    year_progress = get_year_progress()
    logger.info(f"Year progress: {year_progress}")
    
    # 分析诗词主题（用于备选图片）
    try:
        theme, analysis = analyze_poetry_theme(sentence)
        logger.info(f"Analyzed poetry theme: {theme}")
    except Exception as e:
        logger.error(f"Failed to analyze poetry theme: {e}")
    
    # 尝试生成图片
    try:
        images_list = make_pic_and_save(sentence)
        
        # 如果图片生成失败，尝试使用不同的诗词
        if not images_list:
            logger.warning("First attempt failed, trying with different sentence")
            sentence = get_one_sentence()
            logger.info(f"Trying with new sentence: {sentence}")
            
            # 重新分析新诗词的主题
            try:
                theme, analysis = analyze_poetry_theme(sentence)
            except Exception as e:
                logger.error(f"Failed to analyze new poetry theme: {e}")
            
            images_list = make_pic_and_save(sentence)
            
    except Exception as e:
        logger.error(f"Image generation failed completely: {e}")
        images_list = []
    
    # 如果仍然没有图片，使用备选方案
    if not images_list:
        logger.info("Using fallback image")
        fallback_image = get_fallback_image(theme, analysis)
        images_list = [fallback_image]
    
    logger.info(f"Final result: {len(images_list)} images available")
    return sentence, is_get_up_early, images_list, year_progress


def main(
    github_token,
    repo_name,
    weather_message,
    tele_token,
    tele_chat_id,
):
    u = login(github_token)
    repo = u.get_repo(repo_name)
    issue = repo.get_issue(GET_UP_ISSUE_NUMBER)
    is_today = get_today_get_up_status(issue)
    
    sentence, is_get_up_early, images_list, year_progress = make_get_up_message()
    get_up_time = pendulum.now(TIMEZONE).to_datetime_string()
    body = GET_UP_MESSAGE_TEMPLATE.format(get_up_time=get_up_time, sentence=sentence, year_progress=year_progress)
    early_message = body
    
    if weather_message:
        weather_message = f"现在的天气是{weather_message}°\n"
        body = weather_message + early_message
    
    
    if is_get_up_early:
        # GitHub评论只显示第一张图片（通常是FastGPT生成的）
        if images_list and len(images_list) > 0:
            image_url = images_list[0]
            comment = body + f"![image]({image_url})"
            logger.info(f"GitHub comment will include image: {image_url}")
            
            # 检查图片类型
            if image_url in STATIC_FALLBACK_IMAGES:
                comment += "\n\n*使用备选图片*"
                logger.info("Using static fallback image for GitHub comment")
            elif "fastgpt" in image_url.lower() or "flux" in image_url.lower():
                comment += "\n\n*AI生成图片*"
                logger.info("Using AI generated image for GitHub comment")
            elif "unsplash.com" in image_url.lower():
                comment += "\n\n*智能匹配图片*"
                logger.info("Using Unsplash matched image for GitHub comment")
        else:
            comment = body + "\n\n*今日暂无配图*"
            logger.warning("No images available, posting without image")
        
        # 发送 GitHub 评论
        try:
            issue.create_comment(comment)
            print("GitHub comment posted successfully")
        except Exception as e:
            print(f"Error posting GitHub comment: {str(e)}")
        
        # send to telegram
        if tele_token and tele_chat_id:
            print(f"Attempting to send Telegram message to chat_id: {tele_chat_id}")
            try:
                bot = telebot.TeleBot(tele_token)
                
                if images_list and len(images_list) > 0:
                    logger.info(f"Sending Telegram message with {len(images_list)} images")
                    try:
                        # 分析图片类型
                        has_fastgpt = any("fastgpt" in img.lower() or "flux" in img.lower() for img in images_list)
                        has_unsplash = any("unsplash.com" in img.lower() for img in images_list)
                        has_static = any(img in STATIC_FALLBACK_IMAGES for img in images_list)
                        
                        # 构建图片类型说明
                        image_types = []
                        if has_fastgpt:
                            image_types.append("AI生成图片")
                        if has_unsplash:
                            image_types.append("智能匹配图片")
                        if has_static:
                            image_types.append("备选图片")
                        
                        caption = body
                        if image_types:
                            caption += f"\n\n*图片类型: {', '.join(image_types)}*"
                            logger.info(f"Telegram images types: {', '.join(image_types)}")
                        
                        # 发送最多4张图片
                        photos_list = [InputMediaPhoto(i) for i in images_list[:4]]
                        photos_list[0].caption = caption
                        result = bot.send_media_group(
                            tele_chat_id, photos_list, disable_notification=True
                        )
                        logger.info(f"Telegram media group sent successfully with {len(photos_list)} images")
                    except Exception as e:
                        logger.error(f"Error sending photos to Telegram: {str(e)}")
                        # 如果发送图片失败，发送纯文本消息
                        try:
                            result = bot.send_message(tele_chat_id, body, disable_notification=True)
                            logger.info("Telegram text message sent successfully as fallback")
                        except Exception as text_error:
                            logger.error(f"Error sending text message to Telegram: {str(text_error)}")
                else:
                    # 如果没有图片，只发送文本消息
                    logger.info("Sending Telegram text message only")
                    try:
                        result = bot.send_message(tele_chat_id, body, disable_notification=True)
                        logger.info("Telegram text message sent successfully")
                    except Exception as e:
                        logger.error(f"Error sending text message to Telegram: {str(e)}")
                        
            except Exception as bot_error:
                print(f"Error initializing Telegram bot: {str(bot_error)}")
        else:
            print(f"Telegram not configured - token: {'SET' if tele_token else 'NOT SET'}, chat_id: {'SET' if tele_chat_id else 'NOT SET'}")
    else:
        print("You wake up late")
    
    print("Successfully recorded today's wake up time")
    print("Script execution completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("github_token", help="github_token")
    parser.add_argument("repo_name", help="repo_name")
    parser.add_argument(
        "--weather_message", help="weather_message", nargs="?", default="", const=""
    )
    parser.add_argument(
        "--tele_token", help="tele_token", nargs="?", default="", const=""
    )
    parser.add_argument(
        "--tele_chat_id", help="tele_chat_id", nargs="?", default="", const=""
    )
    options = parser.parse_args()
    main(
        options.github_token,
        options.repo_name,
        options.weather_message,
        options.tele_token,
        options.tele_chat_id,
    )
