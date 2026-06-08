"""
推文监控模块 - 定时轮询目标账户，检测新推文
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from twitscrape import Tweet


class TweetMonitor:
    """持续监控指定 X 账户的新推文"""

    # 状态记录文件，用于持久化已处理的推文 ID
    STATE_FILE = "monitor_state.json"

    def __init__(self, client, check_interval: int = 60):
        """
        Args:
            client: twitscrape 客户端实例
            check_interval: 检查间隔（秒），默认 60 秒
        """
        self.client = client
        self.check_interval = check_interval
        self._running = False
        self._task = None
        self._known_tweet_ids = set()
        self._on_new_tweet_callbacks = []
        self._on_error_callbacks = []
        self._on_status_change_callbacks = []

    def add_on_new_tweet(self, callback: Callable[[Tweet], None]):
        """注册新推文回调"""
        self._on_new_tweet_callbacks.append(callback)

    def add_on_error(self, callback: Callable[[str], None]):
        """注册错误回调"""
        self._on_error_callbacks.append(callback)

    def add_on_status_change(self, callback: Callable[[str], None]):
        """注册状态变化回调"""
        self._on_status_change_callbacks.append(callback)

    def _notify_new_tweet(self, tweet: Tweet):
        for cb in self._on_new_tweet_callbacks:
            try:
                cb(tweet)
            except Exception as e:
                print(f"新推文回调执行出错: {e}")

    def _notify_error(self, message: str):
        for cb in self._on_error_callbacks:
            try:
                cb(message)
            except Exception:
                pass

    def _notify_status(self, status: str):
        for cb in self._on_status_change_callbacks:
            try:
                cb(status)
            except Exception:
                pass

    def _load_state(self, target_user: str):
        """从文件加载已知的推文 ID"""
        state_path = os.path.join(self._get_state_dir(target_user), self.STATE_FILE)
        if os.path.exists(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._known_tweet_ids = set(data.get("known_ids", []))
            except Exception:
                self._known_tweet_ids = set()

    def _save_state(self, target_user: str):
        """保存已知的推文 ID 到文件"""
        state_dir = self._get_state_dir(target_user)
        os.makedirs(state_dir, exist_ok=True)
        state_path = os.path.join(state_dir, self.STATE_FILE)
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump({
                "known_ids": list(self._known_tweet_ids),
                "last_check": datetime.now().isoformat(),
            }, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _get_state_dir(target_user: str) -> str:
        """获取状态存储目录"""
        return os.path.join("data", target_user)

    async def _fetch_latest_tweets(self, user_id: str, count: int = 20):
        """获取目标用户的最新推文"""
        try:
            tweets = await self.client.get_user_tweets(user_id, "Tweets", count=count)
            return tweets
        except Exception as e:
            self._notify_error(f"获取推文失败: {e}")
            return []

    async def _check_for_updates(self, user_id: str, target_user: str):
        """检查是否有新推文"""
        self._notify_status("正在检查新推文...")
        tweets = await self._fetch_latest_tweets(user_id)

        if not tweets:
            self._notify_status("未获取到推文，可能触发了速率限制")
            return

        new_tweets = []
        for tweet in tweets:
            if tweet.id not in self._known_tweet_ids:
                self._known_tweet_ids.add(tweet.id)
                new_tweets.append(tweet)

        if new_tweets:
            self._save_state(target_user)
            for tweet in new_tweets:
                self._notify_new_tweet(tweet)

        self._notify_status(
            f"检查完成 - 新推文: {len(new_tweets)} 条 | "
            f"下次检查: {self.check_interval}秒后"
        )

    async def _monitor_loop(self, user_id: str, target_user: str):
        """监控主循环"""
        # 初始化：加载状态，获取最新推文作为基准
        self._load_state(target_user)
        self._notify_status("正在初始化，获取最新推文作为基准...")

        tweets = await self._fetch_latest_tweets(user_id, count=10)
        if tweets:
            for tweet in tweets:
                self._known_tweet_ids.add(tweet.id)
            self._save_state(target_user)
            self._notify_status(
                f"初始化完成，已记录 {len(tweets)} 条历史推文。开始监控..."
            )
        else:
            self._notify_status("初始化未获取到推文，将等待下次检查...")

        # 主循环
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                if not self._running:
                    break
                await self._check_for_updates(user_id, target_user)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._notify_error(f"监控循环出错: {e}")
                await asyncio.sleep(30)  # 出错后等待 30 秒再试

    async def start(self, username: str):
        """
        开始监控指定用户

        Args:
            username: 要监控的 X 用户名（不含 @）
        """
        if self._running:
            self._notify_error("监控已在运行中")
            return

        self._running = True
        self._notify_status(f"正在解析用户 @{username} ...")

        try:
            # 解析用户名获取 user_id
            try:
                user = await self.client.user_by_username(username)
            except Exception as e:
                self._notify_error(f"无法查找用户 @{username}: {e}")
                self._running = False
                return

            if not user:
                self._notify_error(f"无法找到用户 @{username}")
                self._running = False
                return

            try:
                user_id = str(user.id)
            except (AttributeError, TypeError):
                self._notify_error(f"用户 @{username} 数据格式异常")
                self._running = False
                return
            self._notify_status(f"已找到用户: @{username} (ID: {user_id})")

            # 启动监控循环
            self._task = asyncio.create_task(self._monitor_loop(user_id, username))
        except Exception as e:
            self._notify_error(f"启动监控失败: {e}")
            self._running = False

    def stop(self):
        """停止监控"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._notify_status("监控已停止")

    @property
    def is_running(self) -> bool:
        return self._running
