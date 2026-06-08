"""
内容下载模块 - 下载推文的文本、图片和视频到本地
支持按用户名分类文件夹、自动重命名、保持原始格式
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from twitscrape import Tweet


class TweetDownloader:
    """下载推文的全部内容到本地"""

    def __init__(self, base_dir: str = "downloads"):
        """
        Args:
            base_dir: 下载根目录
        """
        self.base_dir = base_dir

    def _get_user_dir(self, username: str) -> str:
        """获取用户专属目录"""
        return os.path.join(self.base_dir, username)

    def _get_unique_path(self, directory: str, filename: str) -> str:
        """
        获取不重复的文件路径，如果文件已存在则自动重命名
        例如: photo.jpg -> photo_1.jpg -> photo_2.jpg
        """
        base, ext = os.path.splitext(filename)
        filepath = os.path.join(directory, filename)
        counter = 1
        while os.path.exists(filepath):
            new_filename = f"{base}_{counter}{ext}"
            filepath = os.path.join(directory, new_filename)
            counter += 1
        return filepath

    def _sanitize_filename(self, filename: str, max_length: int = 100) -> str:
        """清理文件名，移除非法字符"""
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        if len(filename) > max_length:
            filename = filename[:max_length]
        return filename.strip()

    async def download_tweet(self, tweet: Tweet, username: str,
                             on_progress: callable = None):
        """
        下载单条推文的全部内容

        文件结构:
        downloads/
        └── 用户名/
            ├── images/          # 图片 (jpg/png)
            ├── videos/          # 视频 (mp4)
            └── texts/           # 推文文本 (json)

        Args:
            tweet: twitscrape Tweet 对象
            username: 推文所属用户名
            on_progress: 进度回调函数 (message: str)
        """
        user_dir = self._get_user_dir(username)
        images_dir = os.path.join(user_dir, "images")
        videos_dir = os.path.join(user_dir, "videos")
        texts_dir = os.path.join(user_dir, "texts")

        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(videos_dir, exist_ok=True)
        os.makedirs(texts_dir, exist_ok=True)

        downloaded_files = []
        tweet_id = str(tweet.id)

        # 1. 保存推文文本元数据
        metadata = self._extract_metadata(tweet)
        text_filename = f"{tweet_id}.json"
        text_filepath = self._get_unique_path(texts_dir, text_filename)
        with open(text_filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        downloaded_files.append(text_filepath)

        if on_progress:
            on_progress(f"已保存推文文本: {tweet_id}")

        # 2. 下载媒体文件（图片和视频）
        if hasattr(tweet, 'media') and tweet.media:
            for i, media in enumerate(tweet.media):
                try:
                    if media.type == "photo":
                        # 获取原始扩展名，默认为 jpg
                        original_url = getattr(media, 'url', '')
                        ext = self._get_image_ext(original_url)
                        filename = f"{tweet_id}_photo_{i + 1}.{ext}"
                        filepath = self._get_unique_path(images_dir, filename)
                        await media.download(filepath)
                        downloaded_files.append(filepath)
                        if on_progress:
                            on_progress(f"已下载图片: {os.path.basename(filepath)}")

                    elif media.type == "video":
                        if hasattr(media, 'streams') and media.streams:
                            best_stream = media.streams[-1]
                            filename = f"{tweet_id}_video_{i + 1}.mp4"
                            filepath = self._get_unique_path(videos_dir, filename)
                            await best_stream.download(filepath)
                            downloaded_files.append(filepath)
                            if on_progress:
                                on_progress(f"已下载视频: {os.path.basename(filepath)}")
                        else:
                            if on_progress:
                                on_progress(f"视频无可用流，跳过")

                    elif media.type == "animated_gif":
                        filename = f"{tweet_id}_gif_{i + 1}.mp4"
                        filepath = self._get_unique_path(videos_dir, filename)
                        if hasattr(media, 'streams') and media.streams:
                            await media.streams[-1].download(filepath)
                            downloaded_files.append(filepath)
                            if on_progress:
                                on_progress(f"已下载 GIF: {os.path.basename(filepath)}")

                except Exception as e:
                    if on_progress:
                        on_progress(f"下载媒体失败 (index={i}): {e}")

        return downloaded_files

    @staticmethod
    def _get_image_ext(url: str) -> str:
        """从 URL 中提取图片扩展名"""
        if not url:
            return "jpg"
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            # webp 转换为 jpg 更通用
            return "jpg" if ext == ".webp" else ext.lstrip(".")
        return "jpg"

    def _extract_metadata(self, tweet: Tweet) -> dict:
        """提取推文元数据"""
        media_info = []
        if hasattr(tweet, 'media') and tweet.media:
            for m in tweet.media:
                media_info.append({
                    "type": m.type,
                    "url": getattr(m, 'url', ''),
                })

        return {
            "id": str(tweet.id),
            "text": getattr(tweet, 'text', ''),
            "created_at": getattr(tweet, 'created_at', ''),
            "author": {
                "id": str(getattr(tweet.user, 'id', '')) if hasattr(tweet, 'user') else '',
                "username": getattr(tweet.user, 'screen_name', '') if hasattr(tweet, 'user') else '',
                "name": getattr(tweet.user, 'name', '') if hasattr(tweet, 'user') else '',
            },
            "media": media_info,
            "lang": getattr(tweet, 'lang', ''),
            "retweet_count": getattr(tweet, 'retweet_count', 0),
            "like_count": getattr(tweet, 'like_count', 0),
            "reply_count": getattr(tweet, 'reply_count', 0),
            "view_count": getattr(tweet, 'view_count', 0),
            "bookmarks": getattr(tweet, 'bookmarks', 0),
            "downloaded_at": datetime.now().isoformat(),
        }

    async def download_batch(self, tweets: list, username: str,
                             on_progress: callable = None) -> list:
        """
        批量下载多条推文
        """
        all_files = []
        for i, tweet in enumerate(tweets):
            if on_progress:
                on_progress(f"正在处理第 {i + 1}/{len(tweets)} 条推文...")
            try:
                files = await self.download_tweet(tweet, username, on_progress)
                all_files.extend(files)
            except Exception as e:
                if on_progress:
                    on_progress(f"处理推文 {tweet.id} 失败: {e}")

        if on_progress:
            on_progress(f"批量下载完成！共下载 {len(all_files)} 个文件")
        return all_files
