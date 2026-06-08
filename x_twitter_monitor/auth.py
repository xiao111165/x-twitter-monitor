"""
Cookie 认证模块 - 管理 X (Twitter) 的 Cookie 认证
支持从 JSON 文件加载 Cookie 或手动输入
"""

import json
import os
from pathlib import Path
from typing import Optional

from twitscrape import create_client_from_file, create_client


class AuthManager:
    """管理 X (Twitter) 的 Cookie 认证"""

    DEFAULT_COOKIE_FILE = "cookies.json"

    def __init__(self, cookie_file: str = None):
        self.cookie_file = cookie_file or self.DEFAULT_COOKIE_FILE
        self._client = None

    @staticmethod
    def create_cookie_file(path: str, auth_token: str, ct0: str, twid: str = "") -> str:
        """
        创建 Cookie JSON 文件

        Args:
            path: 保存路径
            auth_token: X 的 auth_token Cookie
            ct0: X 的 ct0 (CSRF token) Cookie
            twid: X 的 twid Cookie (可选)
        """
        cookies = {
            "auth_token": auth_token,
            "ct0": ct0,
        }
        if twid:
            cookies["twid"] = twid

        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)

        return path

    def cookie_file_exists(self) -> bool:
        """检查 Cookie 文件是否存在"""
        return os.path.exists(self.cookie_file)

    def load_cookies_from_file(self) -> dict:
        """从文件加载 Cookie"""
        with open(self.cookie_file, "r", encoding="utf-8") as f:
            return json.load(f)

    async def create_client(self, auth_token: str = None, ct0: str = None,
                            twid: str = None) -> object:
        """
        创建已认证的 X 客户端

        优先使用传入的参数，否则从 Cookie 文件加载

        Args:
            auth_token: X 的 auth_token
            ct0: X 的 ct0
            twid: X 的 twid

        Returns:
            twitscrape 客户端实例
        """
        if auth_token and ct0:
            cookies = {"auth_token": auth_token, "ct0": ct0}
            if twid:
                cookies["twid"] = twid
            self._client = await create_client(cookies)
        elif self.cookie_file_exists():
            self._client = await create_client_from_file(self.cookie_file)
        else:
            raise ValueError(
                "未提供 Cookie 信息，且未找到 Cookie 文件。\n"
                "请通过 GUI 输入 auth_token 和 ct0，或放置 cookies.json 文件。"
            )

        return self._client

    @property
    def client(self):
        """获取当前客户端实例"""
        return self._client

    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self._client is not None
