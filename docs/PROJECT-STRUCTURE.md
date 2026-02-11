# BOCHK 监控系统 - 项目结构图

```
bochk_monitor/
│
├── 📦 src/                         # 源代码模块
│   ├── __init__.py                 # 包入口，导出公共 API
│   ├── config.py                   # 配置管理（.env + config.json）
│   ├── logger.py                   # 日志系统（文件轮转）
│   ├── utils.py                    # 工具函数（sleep_display）
│   ├── send_email.py               # 邮件发送（多提供商）
│   ├── monitor.py                  # 监控核心逻辑
│   └── app.py                      # Flask Web 应用
│
├── ⚙️ config/                      # 配置文件
│   ├── config.json                 # 运行时配置（敏感，不提交）
│   └── config.example.json         # 配置模板（提交）
│
├── 📚 docs/                        # 文档
│   ├── README-RAILWAY.md           # Railway 详细部署指南
│   ├── QUICKSTART-RAILWAY.md       # 快速开始（3分钟）
│   ├── RAILWAY-CHECKLIST.md        # 操作检查清单
│   └── RAILWAY-DEPLOY-SUMMARY.md   # 部署总结
│
├── 🎨 templates/                   # Flask 模板
│   ├── index.html                  # 主页面（监控面板）
│   └── history.html                # 历史记录页面
│
├── 📝 logs/                        # 日志文件（自动创建）
│   └── bochk_monitor.log           # 应用日志
│
├── 🚀 入口点和脚本
│   ├── web.py                      # Web 服务入口（Railway web）
│   ├── monitor.py                  # Worker 服务入口（Railway worker）
│   ├── test_structure.py           # 项目结构验证
│   ├── test_railway_config.py      # 配置测试
│   └── cleanup_old_files.py        # 清理脚本
│
├── 📄 配置文件
│   ├── .env.example                # 环境变量模板
│   ├── Procfile                    # Railway 部署配置
│   ├── runtime.txt                 # Python 版本（3.11.9）
│   ├── requirements.txt            # Python 依赖
│   └── .gitignore                  # Git 忽略配置
│
├── 📖 文档
│   ├── README.md                   # 主项目文档
│   ├── REFACTOR-GUIDE.md           # 重构指南
│   ├── REFACTOR-SUMMARY.md         # 重构总结
│   └── CHECKLIST.md                # 完成检查清单
│
└── 🔧 开发环境
    ├── .venv/                      # Python 虚拟环境（不提交）
    ├── __pycache__/                # Python 缓存（不提交）
    └── .idea/                      # IDE 配置（不提交）
```

---

## 模块关系图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户访问层                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Web 浏览器  ←→  Railway (Gunicorn)  ←→  web.py           │
│                                                             │
│  后台定时任务  ←→  Railway (Worker)  ←→  monitor.py        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        应用层                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  src/app.py (Flask)          src/monitor.py (监控)         │
│  ├── MonitorState            ├── get_jsonAvailableDateAndTime│
│  ├── 路由处理                ├── parse                      │
│  └── Web UI                  └── main                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        核心模块层                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  src/config.py         src/logger.py        src/utils.py   │
│  ├── load_config       ├── logger           ├── sleep_display│
│  ├── save_config       └── 日志轮转          └── 工具函数    │
│  └── 配置优先级                                             │
│                                                             │
│  src/send_email.py                                          │
│  ├── send_email                                             │
│  ├── EMAIL_PROVIDERS                                        │
│  └── 多提供商支持                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        数据层                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  config/config.json         .env              logs/         │
│  (运行时配置)               (环境变量)        (日志文件)    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        外部服务                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  BOCHK API              SMTP 服务                           │
│  (预约系统)             (QQ/Gmail/Outlook/Office365)        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 数据流

### Web 服务流程

```
用户浏览器
    ↓ HTTP 请求
Railway (Gunicorn)
    ↓ WSGI
web.py (入口)
    ↓ import
src/app.py (Flask 应用)
    ↓ 调用
src/monitor.py (监控逻辑)
    ↓
BOCHK API (检查可用性)
    ↓ 响应
src/app.py (更新状态)
    ↓ 渲染
templates/index.html
    ↓ HTTP 响应
用户浏览器 (显示)
```

### Worker 服务流程

```
Railway Worker
    ↓ 启动
monitor.py (入口)
    ↓ import
src/monitor.py (main 函数)
    ↓ 配置加载
src/config.py
    ↓ 循环轮询
BOCHK API
    ↓ 发现可用
src/send_email.py
    ↓
SMTP 服务器 (发送邮件通知)
    ↓ 记录日志
src/logger.py
    ↓
logs/bochk_monitor.log
```

### 配置加载流程

```
应用启动
    ↓
src/config.py (load_config)
    ↓
1️⃣ 检查环境变量 (.env)
    ↓ 存在？
    是 → 使用环境变量 ✅ 优先级最高
    否 ↓
2️⃣ 检查 config/config.json
    ↓ 存在？
    是 → 使用 config.json ✅ 优先级中等
    否 ↓
3️⃣ 使用默认值 ✅ 优先级最低
    ↓
返回配置字典
```

---

## 部署架构（Railway）

```
┌─────────────────────────────────────────────┐
│              GitHub Repository               │
│         (bochk_monitor)                      │
└─────────────────────────────────────────────┘
                    ↓ 推送代码
┌─────────────────────────────────────────────┐
│              Railway Platform                │
├─────────────────────────────────────────────┤
│                                             │
│  Service 1: Web                             │
│  ├── Procfile: web                          │
│  ├── Command: gunicorn web:app              │
│  ├── Port: $PORT                            │
│  └── Public URL: https://xxx.railway.app    │
│                                             │
│  Service 2: Worker (可选)                   │
│  ├── Procfile: worker                       │
│  ├── Command: python monitor.py             │
│  └── 后台运行                               │
│                                             │
│  Environment Variables                      │
│  ├── MAIL_HOST, MAIL_USER, MAIL_PASS       │
│  ├── MONITOR_ALL_DATES, INTERVAL_SECONDS   │
│  └── FLASK_SECRET_KEY                       │
│                                             │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              External Services               │
├─────────────────────────────────────────────┤
│                                             │
│  BOCHK API          SMTP 服务器             │
│  (预约检查)         (邮件通知)              │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 文件依赖关系

```
web.py
  ├── src.app (Flask 应用)
  │   ├── src.config (配置)
  │   ├── src.logger (日志)
  │   ├── src.monitor (监控逻辑)
  │   │   ├── src.config
  │   │   ├── src.logger
  │   │   └── src.utils
  │   └── src.send_email (邮件)
  │       ├── src.config
  │       └── src.logger
  └── templates/*.html

monitor.py
  └── src.monitor (main 函数)
      ├── src.config
      ├── src.logger
      ├── src.utils
      └── src.send_email
          ├── src.config
          └── src.logger
```

---

## 配置文件关系

```
.env.example (模板)
  ↓ 复制并填写
.env (本地开发)
  ↓ Railway 中设置
环境变量 (生产环境)
  ↓ 加载
src/config.py
  ↓ 读取
config/config.json (运行时配置)
  ↓ Web UI 修改
保存回 config/config.json
```

---

此项目结构图展示了完整的模块化架构，包括：

- 📦 清晰的代码组织
- 🔄 完整的数据流
- 🚀 Railway 部署架构
- 📂 文件依赖关系
- ⚙️ 配置加载流程
