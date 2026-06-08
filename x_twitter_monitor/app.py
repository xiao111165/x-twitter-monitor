"""
X (Twitter) 账户监控器 - GUI 应用
支持多账户监控、预设刷新频率、按人分类文件夹
"""

import asyncio
import json
import os
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from .auth import AuthManager
from .monitor import TweetMonitor
from .downloader import TweetDownloader


class XMonitorApp:
    """X (Twitter) 账户监控器 GUI 应用"""

    # 预设刷新频率（秒）
    PRESET_INTERVALS = {
        "1小时 (3600秒)": 3600,
        "5小时 (18000秒)": 18000,
        "30分钟 (1800秒)": 1800,
        "10分钟 (600秒)": 600,
        "1分钟 (60秒)": 60,
        "自定义": None,
    }

    def __init__(self):
        self.root = tb.Window(
            title="X (Twitter) 账户监控器",
            themename="cosmo",
            size=(900, 700),
            minsize=(800, 600),
        )
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 核心组件
        self.auth_manager = AuthManager()
        self.downloader = None
        self._loop = None
        self._loop_thread = None

        # 多账户监控管理
        self._monitors = {}  # {username: TweetMonitor}
        self._monitor_tasks = {}  # {username: asyncio.Task}

        # 状态
        self._is_authenticated = False
        self._download_dir = os.path.join(os.getcwd(), "downloads")

        # 构建 UI
        self._build_ui()

    def _build_ui(self):
        """构建用户界面"""
        # ---- 顶部区域：认证配置 ----
        auth_frame = tb.LabelFrame(
            self.root, text=" 🔑 Cookie 认证 ", padding=10
        )
        auth_frame.pack(fill=X, padx=10, pady=(10, 5))

        # auth_token
        row1 = tb.Frame(auth_frame)
        row1.pack(fill=X, pady=2)
        tb.Label(row1, text="auth_token:", width=14).pack(side=LEFT)
        self.auth_token_var = tk.StringVar()
        self.auth_token_entry = tb.Entry(row1, textvariable=self.auth_token_var, show="*")
        self.auth_token_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        # ct0
        row2 = tb.Frame(auth_frame)
        row2.pack(fill=X, pady=2)
        tb.Label(row2, text="ct0:", width=14).pack(side=LEFT)
        self.ct0_var = tk.StringVar()
        self.ct0_entry = tb.Entry(row2, textvariable=self.ct0_var, show="*")
        self.ct0_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        # twid (可选)
        row3 = tb.Frame(auth_frame)
        row3.pack(fill=X, pady=2)
        tb.Label(row3, text="twid (可选):", width=14).pack(side=LEFT)
        self.twid_var = tk.StringVar()
        self.twid_entry = tb.Entry(row3, textvariable=self.twid_var)
        self.twid_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

        # 认证按钮行
        btn_row = tb.Frame(auth_frame)
        btn_row.pack(fill=X, pady=(5, 0))

        self.auth_btn = tb.Button(
            btn_row, text="🔐 连接认证", command=self._do_auth,
            bootstyle=PRIMARY, width=14
        )
        self.auth_btn.pack(side=LEFT, padx=(0, 5))

        self.cookie_file_btn = tb.Button(
            btn_row, text="📂 从文件加载", command=self._load_cookie_file,
            bootstyle=INFO, width=14
        )
        self.cookie_file_btn.pack(side=LEFT, padx=(0, 5))

        self.auth_status_var = tk.StringVar(value="⏳ 未认证")
        self.auth_status_label = tb.Label(
            btn_row, textvariable=self.auth_status_var,
            bootstyle="inverse-warning"
        )
        self.auth_status_label.pack(side=RIGHT)

        # ---- 中部区域：多账户监控管理 ----
        monitor_frame = tb.LabelFrame(
            self.root, text=" 📡 监控账户管理 ", padding=10
        )
        monitor_frame.pack(fill=X, padx=10, pady=5)

        # 添加账户行
        add_row = tb.Frame(monitor_frame)
        add_row.pack(fill=X, pady=2)

        tb.Label(add_row, text="用户名:", width=8).pack(side=LEFT)
        self.target_user_var = tk.StringVar()
        self.target_user_entry = tb.Entry(
            add_row, textvariable=self.target_user_var, width=20
        )
        self.target_user_entry.pack(side=LEFT, padx=(0, 5))

        tb.Label(add_row, text="刷新频率:", width=8).pack(side=LEFT)
        self.interval_preset_var = tk.StringVar(value="1小时 (3600秒)")
        self.interval_combo = ttk.Combobox(
            add_row, textvariable=self.interval_preset_var,
            values=list(self.PRESET_INTERVALS.keys()),
            width=18, state="readonly"
        )
        self.interval_combo.pack(side=LEFT, padx=(0, 5))
        self.interval_combo.bind("<<ComboboxSelected>>", self._on_interval_change)

        # 自定义间隔输入框（默认隐藏）
        self.custom_interval_var = tk.IntVar(value=3600)
        self.custom_interval_entry = tb.Spinbox(
            add_row, from_=10, to=86400, increment=60,
            textvariable=self.custom_interval_var, width=10
        )
        # 初始不显示

        self.add_account_btn = tb.Button(
            add_row, text="➕ 添加监控", command=self._add_account,
            bootstyle=SUCCESS, width=12
        )
        self.add_account_btn.pack(side=LEFT, padx=(10, 0))

        # 下载目录
        dir_row = tb.Frame(monitor_frame)
        dir_row.pack(fill=X, pady=(5, 2))
        tb.Label(dir_row, text="下载目录:", width=8).pack(side=LEFT)
        self.download_dir_var = tk.StringVar(value=self._download_dir)
        self.download_dir_entry = tb.Entry(
            dir_row, textvariable=self.download_dir_var
        )
        self.download_dir_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        tb.Button(
            dir_row, text="浏览...", command=self._browse_download_dir,
            width=8
        ).pack(side=LEFT)

        # 监控账户列表
        list_frame = tb.Frame(monitor_frame)
        list_frame.pack(fill=BOTH, expand=True, pady=(5, 0))

        # Treeview 表格
        columns = ("username", "interval", "status", "last_check", "action")
        self.account_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings",
            height=5, selectmode="browse"
        )
        self.account_tree.heading("username", text="用户名")
        self.account_tree.heading("interval", text="刷新频率")
        self.account_tree.heading("status", text="状态")
        self.account_tree.heading("last_check", text="最后检查")
        self.account_tree.heading("action", text="操作")
        self.account_tree.column("username", width=150)
        self.account_tree.column("interval", width=120)
        self.account_tree.column("status", width=100)
        self.account_tree.column("last_check", width=150)
        self.account_tree.column("action", width=80)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.account_tree.yview)
        self.account_tree.configure(yscrollcommand=vsb.set)
        self.account_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        # 全局控制按钮
        ctrl_row = tb.Frame(monitor_frame)
        ctrl_row.pack(fill=X, pady=(5, 0))

        self.start_all_btn = tb.Button(
            ctrl_row, text="▶ 全部启动", command=self._start_all,
            bootstyle=SUCCESS, width=12
        )
        self.start_all_btn.pack(side=LEFT, padx=(0, 5))

        self.stop_all_btn = tb.Button(
            ctrl_row, text="⏹ 全部停止", command=self._stop_all,
            bootstyle=DANGER, width=12
        )
        self.stop_all_btn.pack(side=LEFT, padx=(0, 5))

        # ---- 底部区域：日志 ----
        log_frame = tb.LabelFrame(
            self.root, text=" 📋 运行日志 ", padding=5
        )
        log_frame.pack(fill=BOTH, expand=True, padx=10, pady=(5, 10))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=10, wrap=tk.WORD,
            state=DISABLED, font=("Consolas", 9)
        )
        self.log_text.pack(fill=BOTH, expand=True)

        # 配置日志颜色标签
        self.log_text.tag_configure("info", foreground="#333333")
        self.log_text.tag_configure("success", foreground="#28a745")
        self.log_text.tag_configure("warning", foreground="#fd7e14")
        self.log_text.tag_configure("error", foreground="#dc3545")
        self.log_text.tag_configure("tweet", foreground="#007bff", font=("Consolas", 9, "bold"))

        # 自动加载 Cookie 文件（如果存在）
        if self.auth_manager.cookie_file_exists():
            self._log("检测到 cookies.json 文件，可点击「从文件加载」按钮加载", "info")

    def _on_interval_change(self, event=None):
        """刷新频率选择变化"""
        preset = self.interval_preset_var.get()
        if preset == "自定义":
            self.custom_interval_entry.pack(side=LEFT, padx=(0, 5), before=self.add_account_btn)
        else:
            self.custom_interval_entry.pack_forget()

    def _get_interval_seconds(self) -> int:
        """获取当前选择的间隔秒数"""
        preset = self.interval_preset_var.get()
        if preset == "自定义":
            return self.custom_interval_var.get()
        return self.PRESET_INTERVALS.get(preset, 3600)

    def _log(self, message: str, tag: str = "info"):
        """向日志面板添加消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state=NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=DISABLED)

    def _browse_download_dir(self):
        """选择下载目录"""
        dir_path = filedialog.askdirectory(
            title="选择下载目录",
            initialdir=self.download_dir_var.get()
        )
        if dir_path:
            self.download_dir_var.set(dir_path)
            self._download_dir = dir_path

    def _load_cookie_file(self):
        """从文件加载 Cookie"""
        file_path = filedialog.askopenfilename(
            title="选择 Cookie 文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialdir=os.getcwd()
        )
        if file_path:
            try:
                self.auth_manager.cookie_file = file_path
                cookies = self.auth_manager.load_cookies_from_file()
                self.auth_token_var.set(cookies.get("auth_token", ""))
                self.ct0_var.set(cookies.get("ct0", ""))
                self.twid_var.set(cookies.get("twid", ""))
                self._log(f"已从文件加载 Cookie: {file_path}", "success")
            except Exception as e:
                self._log(f"加载 Cookie 文件失败: {e}", "error")
                messagebox.showerror("错误", f"加载 Cookie 文件失败:\n{e}")

    def _do_auth(self):
        """执行认证"""
        auth_token = self.auth_token_var.get().strip()
        ct0 = self.ct0_var.get().strip()
        twid = self.twid_var.get().strip()

        if not auth_token or not ct0:
            messagebox.showwarning("提示", "请输入 auth_token 和 ct0（必填项）")
            return

        self.auth_btn.configure(state=DISABLED, text="⏳ 认证中...")
        self._log("正在连接 X (Twitter)...", "info")

        def auth_task():
            async def _auth():
                try:
                    await self.auth_manager.create_client(
                        auth_token=auth_token,
                        ct0=ct0,
                        twid=twid or None
                    )
                    me = await self.auth_manager.client.user()
                    self.root.after(0, lambda: self._on_auth_success(me.screen_name))
                except Exception as e:
                    self.root.after(0, lambda: self._on_auth_error(str(e)))

            self._run_async(_auth())

        threading.Thread(target=auth_task, daemon=True).start()

    def _on_auth_success(self, screen_name: str):
        """认证成功回调"""
        self._is_authenticated = True
        self.auth_btn.configure(state=NORMAL, text="✅ 已认证")
        self.auth_status_var.set(f"✅ 已连接: @{screen_name}")
        self.auth_status_label.configure(bootstyle="inverse-success")
        self._log(f"认证成功！已连接账户: @{screen_name}", "success")

        try:
            cookie_path = "cookies.json"
            AuthManager.create_cookie_file(
                cookie_path,
                self.auth_token_var.get().strip(),
                self.ct0_var.get().strip(),
                self.twid_var.get().strip()
            )
            self._log(f"Cookie 已保存到 {cookie_path}，下次可免输入", "info")
        except Exception:
            pass

    def _on_auth_error(self, error_msg: str):
        """认证失败回调"""
        self._is_authenticated = False
        self.auth_btn.configure(state=NORMAL, text="🔐 连接认证")
        self.auth_status_var.set("❌ 认证失败")
        self.auth_status_label.configure(bootstyle="inverse-danger")
        self._log(f"认证失败: {error_msg}", "error")
        messagebox.showerror("认证失败", f"无法连接到 X (Twitter):\n\n{error_msg}")

    def _add_account(self):
        """添加监控账户到列表"""
        username = self.target_user_var.get().strip().lstrip("@")
        if not username:
            messagebox.showwarning("提示", "请输入要监控的用户名")
            return

        interval = self._get_interval_seconds()

        # 检查是否已存在
        for item in self.account_tree.get_children():
            if self.account_tree.item(item, "values")[0] == username:
                messagebox.showwarning("提示", f"@{username} 已在监控列表中")
                return

        # 添加到表格
        self.account_tree.insert("", tk.END, values=(
            username,
            self._format_interval(interval),
            "⏸ 未启动",
            "-",
            "删除"
        ))

        self._log(f"已添加监控账户: @{username}，刷新频率: {self._format_interval(interval)}", "success")
        self.target_user_var.set("")  # 清空输入框

    def _format_interval(self, seconds: int) -> str:
        """格式化间隔时间为可读字符串"""
        if seconds >= 3600:
            return f"{seconds // 3600}小时"
        elif seconds >= 60:
            return f"{seconds // 60}分钟"
        return f"{seconds}秒"

    def _start_all(self):
        """启动所有监控账户"""
        if not self._is_authenticated:
            messagebox.showwarning("提示", "请先完成 Cookie 认证")
            return

        self._download_dir = self.download_dir_var.get()
        self.downloader = TweetDownloader(base_dir=self._download_dir)

        for item in self.account_tree.get_children():
            values = self.account_tree.item(item, "values")
            username = values[0]
            interval_str = values[1]

            # 解析间隔秒数
            interval = self._parse_interval(interval_str)

            # 更新状态
            self.account_tree.item(item, values=(
                username, interval_str, "🔄 启动中...", "-", "删除"
            ))

            # 启动监控
            self._start_single_monitor(username, interval, item)

    def _parse_interval(self, interval_str: str) -> int:
        """从格式化字符串解析秒数"""
        if "小时" in interval_str:
            return int(interval_str.replace("小时", "")) * 3600
        elif "分钟" in interval_str:
            return int(interval_str.replace("分钟", "")) * 60
        else:
            return int(interval_str.replace("秒", ""))

    def _start_single_monitor(self, username: str, interval: int, tree_item: str):
        """启动单个账户的监控"""
        monitor = TweetMonitor(
            self.auth_manager.client,
            check_interval=interval
        )

        # 注册回调
        monitor.add_on_new_tweet(
            lambda tweet, u=username: self._on_new_tweet(tweet, u)
        )
        monitor.add_on_error(
            lambda msg, u=username: self._on_monitor_error(msg, u)
        )
        monitor.add_on_status_change(
            lambda status, u=username, item=tree_item: self._on_status_change(status, u, item)
        )

        self._monitors[username] = monitor

        def monitor_task():
            async def _run():
                await monitor.start(username)

            self._run_async(_run())

        threading.Thread(target=monitor_task, daemon=True).start()

    def _stop_all(self):
        """停止所有监控"""
        for username, monitor in self._monitors.items():
            monitor.stop()

        self._monitors.clear()

        # 更新所有状态
        for item in self.account_tree.get_children():
            values = list(self.account_tree.item(item, "values"))
            values[2] = "⏸ 已停止"
            self.account_tree.item(item, values=tuple(values))

        self._log("所有监控已停止", "warning")

    def _on_new_tweet(self, tweet, username: str):
        """检测到新推文的回调"""
        text = getattr(tweet, 'text', '') or ''
        text_preview = text[:80] + "..." if len(text) > 80 else text
        self.root.after(0, lambda: self._log(
            f"🐦 [{username}] 新推文 [{tweet.id}]: {text_preview}", "tweet"
        ))

        # 下载推文内容
        def download_task():
            async def _download():
                try:
                    files = await self.downloader.download_tweet(
                        tweet, username,
                        on_progress=lambda msg: self.root.after(
                            0, lambda m=msg: self._log(f"  ↳ [{username}] {m}", "success")
                        )
                    )
                    self.root.after(0, lambda: self._log(
                        f"  ✅ [{username}] 推文 {tweet.id} 下载完成，共 {len(files)} 个文件",
                        "success"
                    ))
                except Exception as e:
                    self.root.after(0, lambda: self._log(
                        f"  ❌ [{username}] 推文 {tweet.id} 下载失败: {e}", "error"
                    ))

            self._run_async(_download())

        threading.Thread(target=download_task, daemon=True).start()

    def _on_monitor_error(self, message: str, username: str):
        """监控错误回调"""
        self.root.after(0, lambda: self._log(f"⚠ [{username}] {message}", "error"))

    def _on_status_change(self, status: str, username: str, tree_item: str):
        """状态变化回调"""
        self.root.after(0, lambda: self._log(f"ℹ [{username}] {status}", "info"))
        # 更新表格中的状态
        self.root.after(0, lambda: self._update_tree_status(tree_item, status))

    def _update_tree_status(self, tree_item: str, status: str):
        """更新表格中的状态列"""
        values = list(self.account_tree.item(tree_item, "values"))
        values[2] = status[:20]  # 截断避免表格过宽
        values[3] = datetime.now().strftime("%H:%M:%S")
        self.account_tree.item(tree_item, values=tuple(values))

    def _run_async(self, coro):
        """在事件循环中运行异步任务"""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            self._loop_thread = threading.Thread(
                target=self._loop.run_forever, daemon=True
            )
            self._loop_thread.start()

        if self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future
        else:
            self._loop.run_until_complete(coro)

    def _on_close(self):
        """窗口关闭处理"""
        self._stop_all()

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        self.root.destroy()

    def run(self):
        """运行应用"""
        self.root.mainloop()
