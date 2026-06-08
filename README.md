# X (Twitter) 账户监控器

持续监控指定的 X（Twitter）账户，自动将新发布的推文内容（文本、图片、视频）下载到本地。

## 功能特性

- 🔄 **持续监控**：定时轮询目标账户，自动检测新推文
- 📥 **全内容下载**：自动下载推文文本、图片、视频、GIF
- 🖥️ **图形界面**：现代化 GUI，操作简单直观
- 🔑 **Cookie 认证**：无需 API Key，使用浏览器 Cookie 登录
- 💾 **状态持久化**：记录已处理的推文，重启后不会重复下载
- 📋 **实时日志**：运行日志面板，实时查看监控状态

## 环境要求

- Python 3.10+
- Windows / macOS / Linux
- 一个已登录 X (Twitter) 的浏览器（用于获取 Cookie）

## 安装步骤

### 1. 克隆或下载项目

```bash
cd x-twitter-monitor
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 获取 X (Twitter) Cookie

由于 X 官方 API 收费，本工具使用 Cookie 认证方式：

1. 在浏览器中打开 [x.com](https://x.com) 并登录你的账号
2. 按 `F12` 打开开发者工具
3. 切换到 **Application** (应用) 标签
4. 左侧找到 **Cookies** → `https://x.com`
5. 找到以下两个 Cookie（必填）：
   - `auth_token` — 复制其值
   - `ct0` — 复制其值
6. （可选）`twid` — 也可复制

> 💡 也可以使用浏览器扩展 [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie) 或 [Cookie-Editor](https://cookie-editor.com/) 一键导出所有 Cookie。

## 使用方法

### 启动程序

```bash
python main.py
```

### 操作流程

1. **输入 Cookie**：将获取的 `auth_token` 和 `ct0` 填入对应输入框
2. **点击「连接认证」**：验证 Cookie 是否有效
3. **设置监控目标**：输入要监控的 X 用户名（不含 @）
4. **设置检查间隔**：建议 30-120 秒（太短可能触发限制）
5. **选择下载目录**：点击「浏览」选择文件保存位置
6. **点击「开始监控」**：程序开始自动监控和下载

### 下载文件结构

```
downloads/
└── 目标用户名/
    ├── 1234567890123456789/          # 推文 ID
    │   ├── tweet.json                # 推文文本和元数据
    │   └── media/
    │       ├── photo_1.jpg            # 图片
    │       └── video_1.mp4            # 视频
    └── 1234567890123456790/
        ├── tweet.json
        └── media/
```

### 打包为 Windows EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "X-Monitor" main.py
```

打包后的 EXE 文件在 `dist/` 目录中。

## 注意事项

- ⚠️ Cookie 有有效期，过期后需要重新获取
- ⚠️ 检查间隔不宜过短（建议 ≥ 30 秒），否则可能触发 X 的速率限制
- ⚠️ 请遵守 X 的使用条款，仅用于个人合法用途
- 💡 首次启动会记录最新推文作为基准，之后只下载新发布的推文

## 技术栈

| 组件 | 技术 |
|------|------|
| X 数据获取 | [twitscraper](https://pypi.org/project/twitscraper/) |
| GUI 框架 | [ttkbootstrap](https://pypi.org/project/ttkbootstrap/) |
| 打包工具 | PyInstaller |

## 许可证

MIT License
