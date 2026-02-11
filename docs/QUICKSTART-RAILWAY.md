# 🚀 Railway 部署 - 快速上手

> **已为 Railway 部署完全优化！** 以下是快速上手的 4 个步骤

## 📋 3 分钟快速检查

```bash
# 1. 创建本地 .env（如果需要本地测试）
cp .env.example .env

# 2. 运行配置测试脚本
python test_railway_config.py

# 3. 测试发送邮件（可选）
python web.py
# 访问 http://localhost:5000，点击"发送测试邮件"
```

---

## 🎯 部署 3 步走

### 步骤 1️⃣：推送代码到 GitHub

```bash
git add .
git commit -m "feat: Railway deployment optimization"
git push origin main
```

### 步骤 2️⃣：Railroad 连接仓库

1. 访问 https://railway.app
2. 用 GitHub 登陆
3. New Project → Deploy from GitHub → 选择仓库

### 步骤 3️⃣：设置 5 个必需环境变量

在 Railway 中点击 "Add Variables"，设置：

```env
# ✅ 邮件配置（必須）
MAIL_HOST=smtp.qq.com
MAIL_USER=你的QQ邮箱@qq.com
MAIL_PASS=QQ邮箱授权码（获取方法见下面）
SENDER=你的QQ邮箱@qq.com
RECEIVERS=收件人@example.com

# ✅ Flask 密钥（必须）
FLASK_SECRET_KEY=生成的随机字符串（运行 python -c "import secrets; print(secrets.token_urlsafe(32))" 生成）

# ✅ 监控模式（推荐）
MONITOR_ALL_DATES=true
MONITOR_INTERVAL_SECONDS=60
```

---

## 🔑 QQ 邮箱授权码获取方法

1. 登陆 QQ 邮箱 (https://mail.qq.com)
2. 点击 **设置** → **账户**
3. 找到 **POP3/SMTP 服务**
4. 点击 **开启**
5. 系统会发送验证码到你的 QQ
6. 验证后系统会生成 **授权码**（不是你的 QQ 密码！）
7. 复制授权码到 `MAIL_PASS` 环保量

---

## 📊 配置优先级

```
Railway 环境变量（最高优先级）
    ↓ 覆盖
config.json（Web UI 修改）
    ↓ 覆盖
代码默认值
```

**含义：** 环境变量设置后会覆盖本地 config.json

---

## ✨ 两种部署模式（选一个）

### 模式 A：仅 Web（推荐初学者）

- ✅ 可视化管理界面
- ✅ 可在网页上修改配置
- ❌ 监控与 Web 共享生命週期

**Procfile 中启用：**

```
web: gunicorn -w 1 -b 0.0.0.0:$PORT web:app
```

### 模式 B：Web + Worker（推荐生产）

- ✅ 独立后台进程
- ✅ 更稳定可靠
- ❌ 资源消耗稍高

**Procfile 中两条都启用：**

```
web: gunicorn -w 1 -b 0.0.0.0:$PORT web:app
worker: python monitor.py
```

---

## 🧪 部署后验证

1. **查看日志**
   - Railway Dashboard → Logs
   - 搜索 "ERROR" 确保没有错误

2. **测试邮件**（Web 模式）
   - 访问 Railway 分配的 URL
   - 滚到下方点击"发送测试邮件"
   - 检查收件邮箱

3. **检查历史记录**
   - Web 中点击"查看历史"
   - 应该看到监控日志

---

## ❓ 常见问题

| Q                  | A                                          |
| ------------------ | ------------------------------------------ |
| 邮件无法发送？     | 检查 MAIL_PASS 是否是授权码（不是密码）    |
| Worker 无法启动？  | 检查两个 Service 是否都创建了              |
| Railway 报错 502？ | 查看 Logs 中的 Python 错误                 |
| 修改配置后无效？   | 检查环境变量是否设置，它优先于 config.json |
| 怎样修改轮询频率？ | 在 Railway 改 MONITOR_INTERVAL_SECONDS     |

---

## 📚 详细文档

- 📖 [完整部署指南](README-RAILWAY.md) - 详细说明和最佳实践
- ✅ [操作清单](RAILWAY-CHECKLIST.md) - 逐步操作流程
- 📊 [部署总结](RAILWAY-DEPLOY-SUMMARY.md) - 总体概览
- 🧪 [测试脚本](../test_railway_config.py) - 本地配置验证

---

## 🎉 就这样！

你的项目已完全优化可以部署到 Railway！

**按顺序执行：**

1. ✅ git push 代码到 GitHub
2. ✅ Railway 中连接 GitHub
3. ✅ 设置 5 个环境变量
4. ✅ 等待自动部署（2-3 分钟）
5. ✅ 测试邮件发送

祝部署顺利! 🚀

---

**问题？** 查看 `README-RAILWAY.md` 中的故障排除部分
