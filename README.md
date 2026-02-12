## BOCHK 预约系统监控工具

一个功能完整的BOCHK预约系统监控工具，提供 Web 管理界面和独立后台监控功能。

### 功能特性

✅ **智能监控逻辑** - 始终监控所有日期并记录日志，但仅对您关心的特定日期发送邮件通知
✅ **Resend 邮件备份** - SMTP 发送失败时自动切换到 Resend API，确保通知不丢失
✅ **Web 安全保护** - 全站 HTTP Basic Auth 访问密码保护，防止未授权访问
✅ **多渠道邮件通知** - 支持 163、QQ、Gmail、Outlook、Office365
✅ **每日日志系统** - 按天生成日志文件，记录原始 API 响应，方便历史追溯与分析
✅ **Web 管理界面** - 基于 Bootstrap 5.3 的现代化 UI，支持自动刷新与历史记录查看
✅ **Railway 云部署** - 完全优化的部署配置，支持一键部署
✅ **配置优先级** - 环境变量 > config.json > 默认值

### 项目结构

```
bochk_monitor/
├── src/                          # 源代码模块
│   ├── __init__.py              # 包初始化
│   ├── config.py                # 配置管理
│   ├── send_email.py            # 邮件发送（SMTP + Resend Fallback）
│   ├── logger.py                # 日志管理与历史记录读取
│   ├── utils.py                 # 实用函数
│   ├── monitor.py               # 核心监控逻辑
│   └── app.py                   # Flask Web 应用
│
├── config/                       # 配置文件目录
│   ├── config.json              # 运行时配置
│   └── config.json.example      # 配置示例
│
├── docs/                         # 文档
│   ├── README-RAILWAY.md        # Railway 部署指南
│   └── ...
│
├── templates/                    # Flask 模板
│   ├── index.html               # 主页面
│   └── history.html             # 历史记录页面
│
├── logs/                         # 日志文件目录（按天轮转）
│
├── web.py                        # Web 服务入口点
├── run_cli.py                    # 命令行监控入口点 (CLI Worker)
├── .env.example                  # 环境变量示例
├── Procfile                      # Railway 部署配置
├── requirements.txt              # Python 依赖
└── README.md                     # 项目说明
```

### 快速开始

#### 1. 本地开发

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入配置（包括邮件、Resend Key、访问密码等）
nano .env

# 安装依赖
pip install -r requirements.txt

# 运行 Web 界面 + 监控后台
python web.py

# 或仅运行后台监控 CLI
python run_cli.py
```

访问 http://localhost:5000 查看 Web 界面（需输入 .env 中配置的账号密码）。

#### 2. Railway 部署

详见 [docs/QUICKSTART-RAILWAY.md](docs/QUICKSTART-RAILWAY.md)

**关键步骤：**
1. 推送代码到 GitHub
2. 在 Railway 连接 GitHub 仓库
3. 设置必需的环境变量（见下文配置说明）
4. 等待部署完成

### 配置说明

#### 环境变量

所有配置都可通过环境变量设置，建议在 `.env` 文件或云平台环境变量中配置：

**基础安全配置（必填）**
```env
ADMIN_USERNAME=admin            # 网站访问用户名
ADMIN_PASSWORD=your_password    # 网站访问密码
FLASK_SECRET_KEY=random_string  # Flask 会话密钥
```

**邮件发送配置**
```env
# 主选：SMTP (支持 163/QQ/Gmail/Office365)
MAIL_HOST=smtp.163.com
MAIL_USER=your_email@163.com
MAIL_PASS=your_auth_code        # 授权码
SENDER=your_email@163.com
RECEIVERS=receiver@example.com

# 备选：Resend API (冗余备份)
RESEND_API_KEY=re_123456789     # Resend API Key
```

**监控参数**
```env
MONITOR_CHECK_DATES=20260213,20260214  # 关注日期
MONITOR_INTERVAL_SECONDS=60            # 轮询间隔
MONITOR_NOTIFY_ON_AVAILABLE=true       # 是否发邮件
```

### 入口点说明

#### `web.py` - Web 服务
启动 Flask Web 应用，提供可视化管理界面、实时状态查看和日志历史分析。

#### `run_cli.py` - CLI Worker 服务
纯后台监控进程，适合无需 Web 界面的服务器环境或作为独立的 Worker 进程运行。

### 支持的邮件提供商

| 提供商    | SMTP 服务器        | 端口    | 说明                                |
| --------- | ------------------ | ------- | ----------------------------------- |
| **163**   | smtp.163.com       | 465/25  | 推荐，国内访问稳定                  |
| **QQ**    | smtp.qq.com        | 465/587 | 需在邮箱设置中开启 SMTP             |
| Gmail     | smtp.gmail.com     | 587     | 需使用应用专用密码                  |
| Office365 | smtp.office365.com | 587     | 标准 Office365 配置                 |

### 常见问题

**Q: 为什么收不到邮件？**
A:
1. 检查 `MAIL_PASS` 是否为授权码（非登录密码）。
2. 检查是否配置了 `RESEND_API_KEY` 作为备用。
3. 确认“关注日期”是否设置正确（系统只对关注日期的放号发送通知）。

**Q: 历史记录里的原始日志是什么？**
A: 系统会记录每次 API 请求返回的完整 JSON 数据，方便您分析中银系统的返回结构和排查问题。

**Q: 如何修改访问密码？**
A: 修改环境变量 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 即可。

### 许可证

MIT
