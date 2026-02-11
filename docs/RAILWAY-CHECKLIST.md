# Railway 部署检查清单

## ✅ 已完成的准备工作

以下文件已为 Railway 部署自动优化：

### 核心文件修改

- ✅ `requirements.txt` - 已添加 gunicorn、python-dotenv 等必要依赖
- ✅ `src/config.py` - 支持从 .env 文件和环境变量读取配置
- ✅ `src/app.py` - 支持 PORT 环境变量，优化 Flask 配置
- ✅ `src/monitor.py` - 支持后台独立运行，增强错误处理
- ✅ `.gitignore` - 添加 .env 排除规则

### 新建文件

- ✅ `Procfile` - Railway 运行指令（web + worker）
- ✅ `runtime.txt` - Python 3.11.9 版本指定
- ✅ `.env.example` - 环境变量模板
- ✅ `docs/ ` - 详细部署文档目录

## 需要你配合的步骤

### 1️⃣ GitHub 仓库设置（必需）

```bash
# 在项目目录运行：
git add .
git commit -m "feat: Railway deployment optimization"
git push origin main
```

**需要的信息：**

- [ ] GitHub 账户已登陆？
- [ ] 项目已推送到 GitHub？
- [ ] 仓库是公开的或已授权？

---

### 2️⃣ Railway 账户和项目创建（必需）

1. 访问 https://railway.app
2. 用 GitHub 登陆（或创建账户）
3. 创建新项目 "New Project" → "Deploy from GitHub"
4. 选择你的 `bochk_monitor` 仓库

**需要的信息：**

- [ ] 已在 Railway 注册？
- [ ] 已授权 Railway 访问 GitHub？
- [ ] 已选择仓库？

---

### 3️⃣ 环境变量配置（必需 - 邮件部分）

在 Railway 项目的 "Variables" 中设置：

#### 邮件参数（必填）

复制以下模板并填入实际值：

```
MAIL_HOST=smtp.qq.com
MAIL_USER=你的QQ邮箱@qq.com
MAIL_PASS=QQ邮箱授权码（不是密码）
SENDER=你的QQ邮箱@qq.com
RECEIVERS=收件人1@example.com,收件人2@example.com
```

**说明：**

- `MAIL_USER` 和 `SENDER` 通常相同
- `MAIL_PASS` 是 QQ 邮箱的授权码，NOT 你的 QQ 密码
- 获取 QQ 授权码：QQ邮箱 → 设置 → 账户 → 开启 SMTP/POP3

**需要的信息：**

- [ ] QQ 邮箱账号？
- [ ] QQ 邮箱授权码？（已在 QQ 邮箱获取）
- [ ] 收件邮箱地址？

#### 监控参数（推荐）

```
MONITOR_ALL_DATES=true
MONITOR_INTERVAL_SECONDS=60
MONITOR_NOTIFY_ON_AVAILABLE=true
```

**说明：**

- `MONITOR_ALL_DATES=true` 会自动监控所有可预约日期
- `MONITOR_INTERVAL_SECONDS` 轮询间隔（秒），建议 60-120
- `MONITOR_NOTIFY_ON_AVAILABLE=true` 有可预约时发邮件

#### Flask 参数（必填）

```
FLASK_SECRET_KEY=your-random-secure-string-here
FLASK_ENV=production
```

**说明：**

- `FLASK_SECRET_KEY` 用于 Web 会话加密，建议使用随机字符串
- 可用命令生成：`python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

### 4️⃣ 选择运行方式（必选择其一）

在 Railway 中有两种方式部署：

#### 方式 A：仅 Web 界面（推荐新手）

✅ 优点：

- 可视化管理界面
- 可在网页上修改配置
- 支持实时查看历史记录

❌ 缺点：

- 监控随 Web 服务状态（Web 停止则监控停止）

**配置方式：**

1. Railway 项目右上角 "Add" → "Database" 或保持默认
2. 启动后，访问 Railway 分配的 URL 即可看到 Web 界面

---

#### 方式 B：Web + Worker 后台（推荐高级）

✅ 优点：

- 独立的后台监控进程，稳定性更高
- 支持 Web 管理 + 后台监控双运行
- 监控进程与 Web 解耦

❌ 缺点：

- 需要两个 Railway Service
- 资源消耗稍高

**配置方式：**

1. 第一个 Service 用 Web 访问：
   ```
   Command: gunicorn -w 1 -b 0.0.0.0:$PORT web:app
   ```
2. 第二个 Service 用于后台监控：
   ```
   Command: python monitor.py
   ```

---

### 5️⃣ 部署和验证

**第一次部署：**

1. Railway 会自动读取 `Procfile` 并部署
2. 查看 "Logs" 标签检查部署是否成功
3. 等待大约 2-3 分钟

**验证部署成功：**

- [ ] Railway 显示 "Healthy" 或 "Your service is live"？
- [ ] 如果是 Web，能访问提供的 URL？
- [ ] Logs 中没有明显错误？

**测试邮件发送（Web 模式）：**

1. 访问 Web URL
2. 滚动到下方"邮件配置"
3. 点击"发送测试邮件"按钮
4. 检查收件邮箱是否收到测试邮件

---

## 配置优先级参考

如果你同时设置了多个配置来源，系统会按此优先级加载：

```
环境变量 (.env on Railway)
         ↓ 覆盖
    config.json (Web 修改保存)
         ↓ 覆盖
    默认值 (DEFAULT_CONFIG)
```

**示例：**

- 如果 Railway 环境变量设置 `MONITOR_INTERVAL_SECONDS=30`
- 但 Web 中修改为 60 后保存到 config.json
- 重启后会优先使用环境变量的 30，config.json 的 60 会被忽略

---

## 常见配置错误及修正

### ❌ 错误 1：邮件无法发送

```
症状：Web 显示 "测试邮件发送失败"
原因：SMTP 凭证不对
解决：
1. 确保 MAIL_USER 是完整邮箱地址（如 2801011889@qq.com）
2. 确保 MAIL_PASS 是授权码（QQ邮箱生成），不是 QQ 密码
3. 确保 QQ 邮箱已启用 SMTP 服务
```

### ❌ 错误 2：Worker 不运行

```
症状：Logs 中显示 Worker 不启动
原因：没有创建第二个 Service，或 config 不能加载
解决：
1. 检查是否创建了两个 Service
2. 检查环境变量 MAIL_HOST 等邮件参数是否完整
3. 查看 Logs 具体错误信息
```

### ❌ 错误 3：Web 无法访问

```
症状：访问 URL 显示 502 Bad Gateway
原因：Flask 启动失败或端口配置不对
解决：
1. 查看 Railway Logs 中的错误
2. 检查 FLASK_SECRET_KEY 是否设置
3. 检查 Python 依赖是否正确安装
```

---

## 快速验证清单

部署后，按以下顺序验证：

- [ ] Railway Logs 中没有 Python 错误
- [ ] Web 界面能访问（如果启用）
- [ ] 邮件配置填写完整
- [ ] 发送测试邮件成功
- [ ] 历史记录中出现检查日志
- [ ] （可选）检查监控命中日期时是否收到邮件

---

## 需要我的关键问题

**部署前请确认：**

1. ✅ QQ 邮箱授权码已获取？
2. ✅ 收件邮箱地址确定？
3. ✅ GitHub 仓库已推送？
4. ✅ 项目仓库是公开的？
5. ✅ 需要 Web 界面还是仅后台监控？

**如果有任何问题，提提供：**

- Railway Logs 中的完整错误信息
- 你设置的环境变量列表（邮箱密码可隐藏）
- 部署执行的具体步骤

---

## 本地测试（可选但推荐）

部署前可以先本地测试：

```bash
# 1. 创建 .env 文件
cp .env.example .env

# 2. 编辑 .env 填入你的实际配置
# nano .env

# 3. 测试 Web 模式
python web.py
# 访问 http://localhost:5000

# 4. 或测试 Worker 模式
python monitor.py
```

---

## 后续维护

### 修改配置

- 直接在 Railway 的 "Variables" 中修改环境变量
- 或在 Web 界面修改并保存

### 查看日志

- Railway 仪表板 → 项目 → Logs 标签

### 重启服务

- Railway 仪表板 → 项目 → Deploy 标签 → 选择部署 → "Redeploy"

### 更新代码

- 本地修改 → git push → Railway 自动重新部署

---

## 支持和帮助

- 📖 详细部署指南：见 `README-RAILWAY.md`
- 🔧 本地开发指南：见顶级目录 README.md
- 🐛 遇到问题：检查 Railway Logs 或查看本清单中的"常见错误"
