# Railway 部署指南

本项目已优化以支持在 [Railway](https://railway.app) 上部署。

## 快速开始

### 1. 准备代码仓库

确保项目已提交到 GitHub，包括以下文件：

- `Procfile` - 定义运行进程
- `runtime.txt` - 指定 Python 版本
- `.env.example` - 环境变量模板
- `requirements.txt` - 依赖列表
- `.gitignore` - 确保 `.env` 和 `config.json` 被排除

### 2. Railway 上创建项目

1. 访问 [Railway Dashboard](https://dashboard.railway.app)
2. 点击 "New Project"
3. 选择 "Deploy from GitHub"
4. 授权并选择你的仓库

### 3. 配置环境变量

在 Railway 项目中，设置以下环境变量：

#### 邮件通知配置（必需）

```
MAIL_HOST=smtp.qq.com
MAIL_USER=your_qq_number@qq.com
MAIL_PASS=your_auth_code
SENDER=your_qq_number@qq.com
RECEIVERS=recipient@example.com,another@example.com
```

#### 监控配置

```
# 选项 1：监控特定日期
MONITOR_CHECK_DATES=20260213,20260214,20260215
MONITOR_INTERVAL_SECONDS=60
MONITOR_NOTIFY_ON_AVAILABLE=true

# 选项 2：监控全部可预约日期（推荐）
MONITOR_ALL_DATES=true
MONITOR_INTERVAL_SECONDS=60
MONITOR_NOTIFY_ON_AVAILABLE=true
```

#### Flask 配置

```
FLASK_SECRET_KEY=your-secure-random-string
FLASK_ENV=production
PORT=5000
```

### 4. 启用服务

Railway 会自动读取 `Procfile` 并启动两种服务：

#### Web 服务

```
web: gunicorn -w 1 -b 0.0.0.0:$PORT web:app
```

- 提供 Web UI 管理界面
- 可在 Web 中动态修改配置
- 访问地址：`https://your-app.railway.app`

#### Worker 服务（可选）

```
worker: python monitor.py
```

- 独立的后台监控进程
- 根据 `.env` 配置自动运行
- 对 Web 界面无依赖

**选择其中一种或两种:**

- 仅 Web：适合用户交互强、需要管理界面的场景
- 仅 Worker：适合纯后台监控、资源受限的场景
- 两者都启动：最灵活，支持 Web 管理 + 独立后台监控

### 5. 配置优先级

系统按以下优先级加载配置：

1. **环境变量 (.env)** - 最高优先级 ✅
2. **config.json** - 其次（常用于 Web UI 修改）
3. **默认值** - 最低级

这意味着：

- Railway 中设置的环境变量会覆盖 config.json
- Web UI 修改会保存到 config.json
- 重启应用时，.env 优先级最高

## 本地开发

### 使用 .env 文件

1. 复制 `.env.example` 为 `.env`：

   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 填入你的配置：

   ```env
   MAIL_HOST=smtp.qq.com
   MAIL_USER=2801011889@qq.com
   MAIL_PASS=your_auth_code
   SENDER=2801011889@qq.com
   RECEIVERS=recipient@example.com
   MONITOR_ALL_DATES=true
   FLASK_SECRET_KEY=dev-secret-key
   ```

3. 运行本地开发服务器：

   ```bash
   # Web 界面 + 监控后台线程
   python web.py

   # 或仅后台监控（从 .env 读取配置）
   python monitor.py
   ```

## 常见问题

### Q: "监控全部"模式如何工作？

A: 启用 `MONITOR_ALL_DATES=true` 后，系统会从 BOCHK API 的 `dateQuota` 中自动监控所有 `!= "F"` 的日期（F 表示无号，其他表示可预约）。

### Q: 可以同时运行 Web 和 Worker 吗？

A: 可以。在 Railway 中：

- 创建两个 Service，分别关联不同的 Procfile 命令
- 或使用 `railway up` 本地同时运行两个进程

### Q: 如何修改监控间隔？

A:

- **Web 中修改**：访问 Web UI，在"轮询设置"中修改，点击保存
- **环境变量修改**：设置 `MONITOR_INTERVAL_SECONDS=30`（单位秒）
- 环境变量优先级更高，会覆盖 Web 中的设置

### Q: 邮件发送失败怎么办？

A:

1. 检查 SMTP 凭证是否正确
2. 确保 QQ 邮箱已启用 SMTP 服务并生成授权码（不是密码）
3. 检查接收邮箱地址格式
4. 在 Web UI 中点击"发送测试邮件"验证配置

### Q: 如何查看日志？

A:

- Railway 仪表板中查看 "Logs"
- 实时监控日志中的所有活动

## 配置示例

### 场景 1：监控特定日期（保守模式）

```env
MONITOR_CHECK_DATES=20260213,20260214,20260215
MONITOR_INTERVAL_SECONDS=120
MONITOR_NOTIFY_ON_AVAILABLE=true
MAIL_HOST=smtp.qq.com
MAIL_USER=2801011889@qq.com
MAIL_PASS=xxxx xxxx xxxx xxxx
SENDER=2801011889@qq.com
RECEIVERS=myemail@example.com
```

### 场景 2：监控全部日期（激进模式）

```env
MONITOR_ALL_DATES=true
MONITOR_INTERVAL_SECONDS=60
MONITOR_NOTIFY_ON_AVAILABLE=true
MAIL_HOST=smtp.qq.com
MAIL_USER=2801011889@qq.com
MAIL_PASS=xxxx xxxx xxxx xxxx
SENDER=2801011889@qq.com
RECEIVERS=myemail@example.com
```

## 支持的环境变量完整列表

| 变量名                        | 说明               | 默认值       | 示例                          |
| ----------------------------- | ------------------ | ------------ | ----------------------------- |
| `MONITOR_ALL_DATES`           | 监控全部可预约日期 | `false`      | `true`/`false`                |
| `MONITOR_CHECK_DATES`         | 监控的具体日期     | 空           | `20260213,20260214`           |
| `MONITOR_INTERVAL_SECONDS`    | 轮询间隔（秒）     | `60`         | `60`/`120`                    |
| `MONITOR_NOTIFY_ON_AVAILABLE` | 可预约时发邮件     | `true`       | `true`/`false`                |
| `MAIL_HOST`                   | SMTP 服务器        | 空           | `smtp.qq.com`                 |
| `MAIL_USER`                   | SMTP 用户名        | 空           | `2801011889@qq.com`           |
| `MAIL_PASS`                   | SMTP 授权码        | 空           | 授权码（非密码）              |
| `SENDER`                      | 发件人邮箱         | 空           | `2801011889@qq.com`           |
| `RECEIVERS`                   | 收件人邮箱         | 空           | `a@example.com,b@example.com` |
| `FLASK_SECRET_KEY`            | Flask 会话密钥     | 默认值       | 任意字符串                    |
| `FLASK_ENV`                   | Flask 环境         | `production` | `development`/`production`    |
| `PORT`                        | Web 端口           | `5000`       | `5000`/`8080`                 |
| `HOST`                        | Web 绑定地址       | `0.0.0.0`    | `0.0.0.0`/`127.0.0.1`         |

## 安全建议

1. ✅ 不要在代码中硬编码敏感信息
2. ✅ 在 Railway 环境变量中存储所有凭证
3. ✅ 定期更换 Flask 的 `FLASK_SECRET_KEY`
4. ✅ 使用 QQ 邮箱授权码而非真实密码
5. ✅ 确保 `.env` 文件在 `.gitignore` 中

## 故障排除

### 日志显示 "No check_dates configured"

- 检查环境变量 `MONITOR_CHECK_DATES` 或 `MONITOR_ALL_DATES` 是否设置
- 确保 config.json 包含有效的日期配置

### Worker 进程不运行

- 检查 Railway 仪表板是否有多个 Service
- 确保指定了正确的 Procfile 命令
- 查看 Logs 中的错误信息

### Web 界面无法访问

- 检查 `PORT` 环境变量是否正确
- 确保防火墙允许入站流量
- 查看 Railway 的部署日志

## 支持

如有问题，请检查：

1. `.env.example` 中的配置示例
2. Railway 仪表板的 Logs 部分
3. 本地测试是否能成功运行
