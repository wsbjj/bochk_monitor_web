## BOCHK 预约系统监控工具

一个功能完整的BOCHK预约系统监控工具，提供 Web 管理界面和独立后台监控功能。

### 功能特性

✅ **智能监控逻辑** - 始终监控所有日期并记录日志，但仅对您关心的特定日期发送邮件通知
✅ **Resend 邮件备份** - SMTP 发送失败时自动切换到 Resend API，确保通知不丢失
✅ **Web 安全保护** - 全站 HTTP Basic Auth 访问密码保护，防止未授权访问
✅ **多渠道邮件通知** - 支持 163、QQ、Gmail、Outlook、Office365
✅ **每日日志系统** - 按天生成日志文件，记录原始 API 响应，方便历史追溯与分析
✅ **持久化存储** - 支持 Docker/Railway 挂载单一数据卷，确保配置和日志不丢失
✅ **Web 管理界面** - 基于 Bootstrap 5.3 的现代化 UI，支持自动刷新与历史记录查看
✅ **Railway 云部署** - 提供 railway.toml 配置文件，支持一键部署
✅ **配置优先级** - 环境变量 > data/config.json > 默认值

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
├── data/                         # 持久化数据目录 (建议挂载 Volume)
│   ├── config.json              # 运行时配置 (可选)
│   ├── config.json.example      # 配置示例
│   └── logs/                    # 日志文件目录（按天轮转）
│
├── docs/                         # 文档
│   ├── RAILWAY-VOLUME-GUIDE.md  # Railway 挂载卷指南
│   ├── QUICKSTART-RAILWAY.md    # Railway 快速部署指南
│   └── ...
│
├── templates/                    # Flask 模板
│   ├── index.html               # 主页面
│   └── history.html             # 历史记录页面
│
├── web.py                        # Web 服务入口点
├── run_cli.py                    # 命令行监控入口点 (CLI Worker)
├── .env.example                  # 环境变量示例
├── railway.toml                  # Railway 部署配置文件
├── Procfile                      # Heroku/Railway 进程配置
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

# 初始化数据目录（如果不存在）
mkdir -p data/logs

# 安装依赖
pip install -r requirements.txt

# 运行 Web 界面 + 监控后台
python web.py

# 或仅运行后台监控 CLI
python run_cli.py
```

访问 http://localhost:5000 查看 Web 界面（需输入 .env 中配置的账号密码）。

#### 2. Railway 部署

本项目已包含 `railway.toml`，可直接部署。

**关键步骤：**
1. 推送代码到 GitHub
2. 在 Railway 连接 GitHub 仓库
3. **重要**：添加一个 Volume 挂载到 `/app/data` (用于持久化保存日志和配置文件)
   - 详见 [docs/RAILWAY-VOLUME-GUIDE.md](docs/RAILWAY-VOLUME-GUIDE.md)
4. 设置必需的环境变量（见下文配置说明）
5. 等待部署完成

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
MAIL_PORT=465                   # 465 (SSL) 或 587 (TLS)
MAIL_USER=your_email@163.com
MAIL_PASS=your_auth_code        # 邮箱授权码
SENDER=your_email@163.com
RECEIVERS=receiver1@gmail.com,receiver2@outlook.com

# 备选：Resend API (当 SMTP 失败时自动使用)
RESEND_API_KEY=re_123456789...
```

**监控配置**
```env
MONITOR_CHECK_DATES=20260213,20260214  # 重点关注日期（逗号分隔）
MONITOR_INTERVAL_SECONDS=120           # 检查间隔（秒）
MONITOR_NOTIFY_ON_AVAILABLE=true       # 有号时是否通知
MONITOR_ALL_DATES=false                # 是否关注所有日期（true则忽略CHECK_DATES）

# 时区配置
TIMEZONE_OFFSET=0                      # 手动设置偏移量 (单位：小时)
                                       # 计算公式：用户时区 - 服务器时区
                                       # 例：用户GMT+8，服务器GMT-4 => 8-(-4)=12
```

#### 配置文件 (可选)

如果你更喜欢使用文件配置，可以在 `data/` 目录下创建 `config.json`：

```bash
cp data/config.json.example data/config.json
```

注意：环境变量的优先级高于 `config.json`。

### 许可证

MIT License
