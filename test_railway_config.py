#!/usr/bin/env python3
"""
本地测试脚本 - 验证 Railway 部署前的配置
使用方法：python test_railway_config.py
"""

import os
import sys
from pathlib import Path

# 添加项目目录到路径
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

try:
    from src.config import load_config
    from src.send_email import send_email
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def check_env_file():
    """检查 .env 文件"""
    print_header("1️⃣  检查 .env 文件")
    
    env_path = project_dir / ".env"
    example_path = project_dir / ".env.example"
    
    if env_path.exists():
        print("✅ .env 文件存在")
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"   包含 {len(lines)} 行配置")
    elif example_path.exists():
        print("⚠️  .env 文件不存在，但 .env.example 存在")
        print("   运行：cp .env.example .env")
        print("   然后编辑 .env 填入实际配置")
    else:
        print("⚠️  .env 和 .env.example 都不存在")


def check_config_loading():
    """检查配置加载"""
    print_header("2️⃣  检查配置加载")
    
    try:
        config = load_config()
        
        # 监控配置
        monitor = config.get("monitor", {})
        print("📊 监控配置:")
        print(f"   - 日期: {monitor.get('check_dates', [])}")
        print(f"   - 间隔: {monitor.get('interval_seconds', 60)} 秒")
        print(f"   - 通知: {'是' if monitor.get('notify_on_available') else '否'}")
        
        # 邮件配置
        email = config.get("email", {})
        print("\n📧 邮件配置:")
        mail_user = email.get('mail_user', '')
        mail_host = email.get('mail_host', '')
        sender = email.get('sender', '')
        receivers = email.get('receivers', [])
        
        if mail_host:
            print(f"   ✅ SMTP 主机: {mail_host}")
        else:
            print(f"   ❌ SMTP 主机: 未配置")
            
        if mail_user:
            print(f"   ✅ 用户名: {mail_user[:10]}...（已配置）")
        else:
            print(f"   ❌ 用户名: 未配置")
            
        if email.get('mail_pass'):
            print(f"   ✅ 授权码: （已配置）")
        else:
            print(f"   ❌ 授权码: 未配置")
            
        if sender:
            print(f"   ✅ 发件人: {sender[:10]}...（已配置）")
        else:
            print(f"   ❌ 发件人: 未配置")
            
        if receivers and receivers != ['']:
            print(f"   ✅ 收件人: {len(receivers)} 个地址")
            for r in receivers:
                if r:
                    print(f"      - {r}")
        else:
            print(f"   ❌ 收件人: 未配置")
        
        # 检查邮件配置是否完整
        print("\n📋 邮件配置完整性:")
        required_fields = ['mail_host', 'mail_user', 'mail_pass', 'sender', 'receivers']
        complete = True
        for field in required_fields:
            if field == 'receivers':
                has_value = email.get(field) and email.get(field) != [''] and any(email.get(field))
            else:
                has_value = bool(email.get(field))
            
            status = "✅" if has_value else "❌"
            print(f"   {status} {field}")
            if not has_value:
                complete = False
        
        return complete
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def check_email_sending():
    """检查邮件发送"""
    print_header("3️⃣  检查邮件发送")
    
    try:
        config = load_config()
        email = config.get("email", {})
        
        # 检查必要字段
        required_fields = ['mail_host', 'mail_user', 'mail_pass', 'sender', 'receivers']
        missing = [f for f in required_fields if not email.get(f)]
        
        if missing:
            print(f"⚠️  邮件配置不完整，缺少: {', '.join(missing)}")
            print("   请在 .env 中补充这些配置")
            return False
        
        print("🔄 尝试发送测试邮件...")
        result = send_email(
            "BOCHK Monitor - 配置测试",
            "这是一封来自 BOCHK 监控系统的测试邮件。\n\n如果你收到这封邮件，说明邮件配置正确！"
        )
        
        if result:
            print("✅ 测试邮件发送成功！")
            print(f"   收件人: {', '.join(email.get('receivers', []))}")
            return True
        else:
            print("❌ 测试邮件发送失败")
            print("   可能原因:")
            print("   1. SMTP 凭证错误（特别是 MAIL_PASS）")
            print("   2. QQ 邮箱未启用 SMTP 服务")
            print("   3. 网络连接问题")
            return False
            
    except Exception as e:
        print(f"❌ 邮件测试异常: {e}")
        return False


def check_env_variables():
    """检查环境变量"""
    print_header("4️⃣  检查环境变量")
    
    important_vars = {
        'MAIL_HOST': '邮件主机',
        'MAIL_USER': '邮箱用户',
        'MAIL_PASS': '邮箱授权码',
        'SENDER': '发件人邮箱',
        'RECEIVERS': '收件人邮箱',
        'MONITOR_ALL_DATES': '监控全部日期',
        'MONITOR_INTERVAL_SECONDS': '轮询间隔',
        'FLASK_SECRET_KEY': 'Flask 密钥',
    }
    
    print("当前环境变量状态:")
    for var, desc in important_vars.items():
        value = os.getenv(var, '')
        if value:
            # 隐藏敏感信息
            if 'PASS' in var or 'KEY' in var:
                display = f"{value[:8]}...***（已隐藏）"
            elif len(value) > 20:
                display = f"{value[:20]}..."
            else:
                display = value
            print(f"   ✅ {var:30} = {display}")
        else:
            print(f"   ⚠️  {var:30} （未设置）")


def generate_secret_key():
    """生成 Flask 密钥"""
    print_header("生成 Flask 密钥")
    
    try:
        import secrets
        key = secrets.token_urlsafe(32)
        print(f"推荐的 FLASK_SECRET_KEY:\n\n   {key}\n")
        print("将其复制到 Railway 的环境变量中")
    except Exception as e:
        print(f"❌ 生成密钥失败: {e}")


def main():
    print("\n")
    print("    🚀 Railway 部署前配置测试")
    print("    " + "="*50)
    
    # 检查 .env 文件
    check_env_file()
    
    # 检查配置加载
    config_ok = check_config_loading()
    
    # 检查邮件发送
    email_ok = False
    if config_ok:
        email_ok = check_email_sending()
    
    # 检查环境变量
    check_env_variables()
    
    # 生成建议密钥
    generate_secret_key()
    
    # 总结
    print_header("测试总结")
    print("✅ 已完成所有检查\n")
    
    if config_ok and email_ok:
        print("🎉 所有配置正确！可以部署到 Railway 了")
        print("\n后续步骤:")
        print("1. git add . && git commit && git push")
        print("2. 在 Railway 中连接 GitHub")
        print("3. 设置环境变量")
        print("4. 等待自动部署完成")
    else:
        print("⚠️  检测到配置问题，请修复后重新测试")
        print("\n常见问题:")
        print("- MAIL_PASS 是 QQ 邮箱授权码，不是密码")
        print("- 确保 .env 文件已创建（cp .env.example .env）")
        print("- 检查收件人邮箱地址是否正确")
        print("- 确保 QQ 邮箱已启用 SMTP 服务")
    
    print("\n")


if __name__ == "__main__":
    main()
