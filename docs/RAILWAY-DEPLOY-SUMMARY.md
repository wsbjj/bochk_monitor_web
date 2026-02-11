# Railway 部署 - 完成总结

## 🎉 已完成的自动优化

### 代码改造

```
✅ src/config.py      → 支持 .env 文件和环境变量
✅ src/app.py         → 支持 PORT 和 FLASK_SECRET_KEY 环境变量
✅ src/monitor.py     → 独立后台运行模式，增强稳定性
✅ requirements.txt   → 添加 gunicorn、python-dotenv
```

### 部署文件

```
✅ Procfile           → 定义 Web 和 Worker 进程
✅ runtime.txt        → 指定 Python 3.11.9
✅ .env.example       → 环境变量模板（安全示例）
✅ .gitignore         → 添加 .env 和 .idea 排除
```

### 文档

```
✅ docs/              → 完整部署文档目录
✅ README-RAILWAY.md  → 详细部署指南和常见问题
✅ RAILWAY-CHECKLIST.md → 逐步操作清单
```

---

## 📋 需要你协调的 3 个关键步骤

### 第 1 步：GitHub 推送

```bash
git add .
git commit -m "feat: Railway deployment optimization"
git push origin main
```

✅ **你需要做：** 推送代码到 GitHub  
⏱️ **耗时：** 1-2 分钟

---

### 第 2 步：Railway 连接

1. 访问 https://railway.app
2. 用 GitHub 登陆
3. "New Project" → "Deploy from GitHub"
4. 选择 `bochk_monitor` 仓库

✅ **你需要做：** 在 Railway 中关联 GitHub 仓库  
⏱️ **耗时：** 3-5 分钟  
❗ **前提：** GitHub 账户已登陆

---

### 第 3 步：配置环境变量

在 Railway 项目的 "Variables" 中設置以下 **必填项**：

#### 📧 邮件配置（必须）

```env
MAIL_HOST=smtp.qq.com
MAIL_USER=你的QQ邮箱@qq.com
MAIL_PASS=QQ邮箱授权码（从QQ邮箱获取，不是密码）
SENDER=你的QQ邮箱@qq.com
RECEIVERS=收件人邮箱1@example.com,收件人邮箱2@example.com
```

#### 🔐 Flask 配置（必须）

```env
FLASK_SECRET_KEY=生成的随机字符串
FLASK_ENV=production
```

#### 📊 监控配置（推荐）

```env
MONITOR_ALL_DATES=true
MONITOR_INTERVAL_SECONDS=60
MONITOR_NOTIFY_ON_AVAILABLE=true
```

✅ **你需要做：** 提供邮箱凭证和收件地址  
⏱️ **耗时：** 5-10 分钟  
❗ **关键注意：** MAIL_PASS 是 QQ 授权码，不是密码！

---

## 🚀 自动部署流程

1. 推送代码后，Railway **自动启动部署**
2. 读取 `Procfile` 中的运行指令
3. 安装 `requirements.txt` 中的依赖
4. 启动 Web 服务（gunicorn）
5. 可选启动 Worker 服务（python monitor.py）

---

## ⚙️ 配置优先级（重要！）

三层配置系统：

```
┌─────────────────────────────────────┐
│  Layer 1: Railway 环境变量 (.env)   │ ← 优先级最高
│  (在 Railway 中设置)                │
├─────────────────────────────────────┤
│  Layer 2: config.json               │ ← 其次
│  (Web UI 修改后自动保存)            │
├─────────────────────────────────────┤
│  Layer 3: 代码中的默认值            │ ← 优先级最低
│  (DEFAULT_CONFIG)                   │
└─────────────────────────────────────┘
```

**含义：**

- Railway 环境变量 > Web 中保存的配置 > 代码默认值
- 部署后修改配置：在 Railway Variables 中改最有效

---

## 📱 两种部署模式

### 模式 A：仅 Web（推荐初学者）

```
Procfile 中启用：web: gunicorn -w 1 -b 0.0.0.0:$PORT web:app
禁用：worker: python monitor.py
```

✅ 特点：有管理界面，可在网页配置  
❌ 缺点：监控进程与 Web 共享（Web 关闭则监控停止）

### 模式 B：Web + Worker（推荐生产环境）

```
两条都启用：
web: gunicorn -w 1 -b 0.0.0.0:$PORT web:app
worker: python monitor.py
```

✅ 特点：独立的后台监控，更稳定  
❌ 缺点：资源占用稍多

**实现两个 Service：**
Railway 中创建两个 Service，分别对应不同的 Procfile 命令行

---

## ✨ 配置示例

### 完整配置（监控全部日期 + 邮件通知）

```env
# 监控全部
MONITOR_ALL_DATES=true
MONITOR_INTERVAL_SECONDS=60
MONITOR_NOTIFY_ON_AVAILABLE=true

# 邮件（QQ 示例）
MAIL_HOST=smtp.qq.com
MAIL_USER=2801011889@qq.com
MAIL_PASS=xxxx xxxx xxxx xxxx
SENDER=2801011889@qq.com
RECEIVERS=myemail@example.com,another@example.com

# Flask
FLASK_SECRET_KEY=my-super-secret-random-string-12345
FLASK_ENV=production
```

### 保守配置（特定日期 + 间隔更长）

```env
# 监控特定日期
MONITOR_ALL_DATES=false
MONITOR_CHECK_DATES=20260213,20260214,20260215
MONITOR_INTERVAL_SECONDS=120
MONITOR_NOTIFY_ON_AVAILABLE=true

# 其他同上...
```

---

## ❓ 常见问题速查

| 问题                         | 答案                                            |
| ---------------------------- | ----------------------------------------------- |
| MAIL_PASS 是什么？           | QQ邮箱的授权码，不是QQ密码。在 QQ邮箱设置中生成 |
| 怎样修改轮询间隔？           | 改 MONITOR_INTERVAL_SECONDS 环境变量，单位秒    |
| 如何查看运行日志？           | Railway Dashboard → Logs 标签                   |
| 能否同时运行 Web 和后台？    | 可以，创建两个 Service，Procfile 中两条都启用   |
| 修改配置后需要重启吗？       | Railway 环境变量修改后自动重启，无需手动        |
| 为什么工作流程无法收到邮件？ | 通常是 MAIL_PASS 错误或 QQ 邮箱未启用 SMTP      |

---

## 📞 遇到问题时

请查看以下顺序：

1. **查阅文档**
   - `README-RAILWAY.md` - 详细指南
   - `RAILWAY-CHECKLIST.md` - 操作清单

2. **检查日志**
   - Railway Dashboard → 项目 → Logs
   - 搜索 "Error" 或 "ERROR"

3. **常见错误修复**
   - 详见 `README-RAILWAY.md` 中的"故障排除"部分
   - 详见 `RAILWAY-CHECKLIST.md` 中的"常见错误"部分

4. **本地验证**
   ```bash
   cp .env.example .env
   # 编辑 .env 填入配置
   python web.py  # 测试 Web
   # 或
   python monitor.py     # 测试后台
   ```

---

## 🎯 后续步骤

### 立即做

- [ ] 复制并推送代码到 GitHub
- [ ] 在 Railway 连接 GitHub 仓库
- [ ] 设置环境变量

### 部署后验证

- [ ] 访问 Railway 分配的 URL
- [ ] 在 Web UI 发送测试邮件
- [ ] 查看 Logs 确认正常运行

### 可选配置

- [ ] 调整 MONITOR_INTERVAL_SECONDS（监控频率）
- [ ] 启用 Worker 进程（独立后台）
- [ ] 配置多个收件人邮箱

---

## 🔗 重要链接

- 🚀 [Railway 官网](https://railway.app)
- 📚 [部署指南](README-RAILWAY.md)
- ✅ [操作清单](RAILWAY-CHECKLIST.md)
- 💻 [本地开发](../README.md)

---

## 📝 总结

✅ **环境已完全优化**  
✅ **支持 .env 文件配置**  
✅ **支持 Railway 部署**  
✅ **代码无需修改**

🚀 **下一步：** 按照 RAILWAY-CHECKLIST.md 的 5 个步骤操作即可！

---

**🎉 祝部署成功！有任何疑问请查阅相关文档。**
