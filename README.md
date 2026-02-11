## BOCHK 预约系统监控工具

一个功能完整的BOCHK预约系统监控工具，提供 Web 管理界面和独立后台监控功能。

### 功能特性

✅ **60 秒轮询监控** - 自动检测预约系统可用性
✅ **Web 管理界面** - 基于 Bootstrap 5.3 的现代化 UI
✅ **多渠道邮件通知** - 支持 QQ、Gmail、Outlook、Office365
✅ **自动日期检测** - "监控全部"模式自动发现可预约日期
✅ **Railway 云部署** - 完全优化的部署配置
✅ **配置优先级** - 环境变量 > config.json > 默认值

### 项目结构

```
bochk_monitor/
├── src/                          # 源代码模块
│   ├── __init__.py              # 包初始化，导出公共 API
│   ├── config.py                # 配置管理（支持 .env 和 config.json）
│   ├── send_email.py            # 多邮件提供商支持
│   ├── logger.py                # 日志配置
│   ├── utils.py                 # 实用函数
│   ├── monitor.py               # 核心监控逻辑和 main() 入口
│   └── app.py                   # Flask Web 应用
│
├── config/                       # 配置文件目录
│   ├── config.json              # 运行时配置（Web 修改保存）
│   └── config.example.json      # 配置示例
│
├── docs/                         # 文档
│   ├── README-RAILWAY.md        # Railway 部署详细指南
│   ├── QUICKSTART-RAILWAY.md    # 快速开始指南
│   ├── RAILWAY-CHECKLIST.md     # 操作检查清单
│   └── RAILWAY-DEPLOY-SUMMARY.md # 部署总结
│
├── templates/                    # Flask 模板
│   ├── index.html               # 主页面
│   └── history.html             # 历史记录页面
│
├── logs/                         # 日志文件目录（自动创建）
│
├── web.py                        # Web 服务入口点
├── monitor.py                    # Worker 服务入口点
├── test_railway_config.py        # 配置测试脚本
│
├── .env.example                  # 环境变量示例
├── Procfile                      # Railway 部署配置
├── runtime.txt                   # Python 版本指定
├── requirements.txt              # Python 依赖
└── .gitignore                    # Git 忽略配置
```

### 快速开始

#### 1. 本地开发

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入配置
nano .env

# 安装依赖
pip install -r requirements.txt

# 运行 Web 界面 + 监控后台
python web.py

# 或仅运行后台监控
python monitor.py
```

访问 http://localhost:5000 查看 Web 界面。

#### 2. Railway 部署

详见 [docs/QUICKSTART-RAILWAY.md](docs/QUICKSTART-RAILWAY.md)

快速流程：

1. 推送代码到 GitHub
2. 在 Railway 连接 GitHub 仓库
3. 设置 5 个必需环境变量（邮件配置 + Flask 密钥 + 监控参数）
4. 等待自动部署完成

### 配置说明

#### 环境变量

所有配置都可通过环境变量设置，支持以下变量：

**邮件配置**

```env
MAIL_HOST=smtp.qq.com           # SMTP 服务器
MAIL_USER=your_email@qq.com     # SMTP 用户
MAIL_PASS=auth_code             # SMTP 授权码/密码
SENDER=your_email@qq.com        # 发件人
RECEIVERS=a@example.com,b@example.com  # 收件人（逗号分隔）
```

**监控配置**

```env
MONITOR_ALL_DATES=true          # 监控全部可预约日期
MONITOR_CHECK_DATES=20260213,20260214  # 或指定特定日期
MONITOR_INTERVAL_SECONDS=60     # 轮询间隔（秒）
MONITOR_NOTIFY_ON_AVAILABLE=true  # 发现可预约时发邮件
```

**Flask 配置**

```env
FLASK_SECRET_KEY=random_string  # 会话密钥
FLASK_ENV=production            # 运行环境
PORT=5000                       # Web 端口
HOST=0.0.0.0                    # Web 绑定地址
```

#### 配置优先级

系统按以下优先级加载配置：

1. **环境变量（最高）** - .env 文件或系统环境变量
2. **config.json** - Web UI 修改后自动保存
3. **默认值（最低）** - 代码中的硬编码默认值

### 入口点说明

#### `web.py` - Web 服务

启动 Flask Web 应用，提供：

- 主管理界面
- 实时监控状态
- 配置管理
- 邮件测试
- 历史记录查看

```bash
python web.py
```

#### `monitor.py` - Worker 服务

独立的后台监控进程，根据 config 或环境变量持续监控，发现可预约时发送邮件通知。

```bash
python monitor.py
```

#### 源代码模块

**src/config.py** - 配置管理

- 从 .env、环境变量、config.json 加载配置
- 支持配置保存
- 默认值管理

**src/monitor.py** - 监控核心

- `get_jsonAvailableDateAndTime()` - 获取 API 响应
- `parse()` - 解析日期可用性
- `main()` - 独立后台监控主函数

**src/app.py** - Flask 应用

- `MonitorState` 类 - 管理监控状态和后台线程
- 路由处理：`/config`、`/test-email`、`/api/next-7-days` 等

**src/send_email.py** - 邮件发送

- 支持多个 SMTP 提供商
- 自动端口检测（465/587）
- 错误处理

**src/logger.py** - 日志管理

- 文件日志轮转
- 控制台输出

**src/utils.py** - 工具函数

- `sleep_display()` - 带进度条的延迟显示

### 支持的邮件提供商

| 提供商    | SMTP 服务器        | 端口    | 获取授权码                          |
| --------- | ------------------ | ------- | ----------------------------------- |
| QQ 邮箱   | smtp.qq.com        | 465/587 | QQ邮箱 → 设置 → 账户 → SMTP/Pop3 |
| Gmail     | smtp.gmail.com     | 587     | Google 账户 → 安全 → 应用密码     |
| Outlook   | smtp.office365.com | 587     | Outlook 账户设置                    |
| Office365 | smtp.office365.com | 587     | Office365 账户设置                  |

### 部署指南

#### 本地部署

1. 安装 Python 3.11+
2. 创建虚拟环境
3. 安装依赖：`pip install -r requirements.txt`
4. 配置 .env 文件
5. 运行 `python web.py` 或 `python monitor.py`

#### Railway 云部署

详见 [docs/QUICKSTART-RAILWAY.md](docs/QUICKSTART-RAILWAY.md)

#### Docker 部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "web:app"]
```

### 常见问题

**Q: 如何修改轮询间隔？**

A: 在 Web UI 中修改，或设置环境变量 `MONITOR_INTERVAL_SECONDS=30`

**Q: 邮件无法发送怎么办？**

A:

1. 确认 MAIL_PASS 是授权码（不是密码）
2. 检查是否启用了 SMTP 服务
3. 在 Web UI 中"发送测试邮件"测试配置

**Q: 监控与 Web 的关系？**

A: 在 web.py 中启动的监控与 Web 会话共享生命周期。使用 monitor.py 可以独立运行监控。

**Q: 能否同时运行 Web 和 Worker？**

A: 可以。在 Railway 中创建两个 Service，分别运行 gunicorn 和 python monitor.py

**Q: 详细文档在哪里？**

A: 查看 `docs/` 目录中的 4 个文档

### 依赖项

- Flask 3.0.3 - Web 框架
- requests - HTTP 客户端
- gunicorn - WSGI 服务器
- python-dotenv - 环境变量管理
- tqdm - 进度条显示
- Bootstrap 5.3 CDN - 前端框架

### 许可证

MIT

### 更新日志

#### v1.0.0 - 初版本

- ✅ 完整的项目结构优化
- ✅ 模块化代码组织
- ✅ 支持多邮件提供商
- ✅ Railway 部署优化
- ✅ Web 管理界面
- ✅ 配置优先级系统

### 支持

- 📖 [详细部署指南](docs/README-RAILWAY.md)
- ✅ [快速开始](docs/QUICKSTART-RAILWAY.md)
- 📊 [操作清单](docs/RAILWAY-CHECKLIST.md)
