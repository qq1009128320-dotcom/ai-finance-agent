#!/bin/bash
# =============================================
# AI智投量化平台 - 腾讯云一键部署脚本
# 适用系统: Ubuntu 22.04 / 20.04
# 使用方法: 
#   1. 登录腾讯云服务器
#   2. 把项目上传到服务器（或 git clone）
#   3. cd 到项目目录
#   4. sudo bash deploy/install.sh
# =============================================

set -e

echo ""
echo "============================================"
echo "  AI智投量化平台 - 部署安装脚本"
echo "============================================"
echo ""

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请用 sudo 运行此脚本: sudo bash deploy/install.sh"
    exit 1
fi

# 项目路径（脚本所在目录的上一级）
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "📁 项目路径: $PROJECT_DIR"

# ---------------------------
# 1. 安装系统依赖
# ---------------------------
echo ""
echo "📦 [1/8] 安装系统依赖..."

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl nginx

echo "   ✅ 系统依赖安装完成"
python3 --version

# ---------------------------
# 2. 创建系统用户（如果不存在）
# ---------------------------
echo ""
echo "👤 [2/8] 创建运行用户..."

if ! id -u www-data &>/dev/null; then
    useradd -r -s /bin/false www-data
fi

# ---------------------------
# 3. 复制项目到目标目录
# ---------------------------
echo ""
echo "📂 [3/8] 部署项目文件..."

APP_DIR="/var/www/ai-quant"
if [ "$PROJECT_DIR" != "$APP_DIR" ]; then
    echo "   复制项目到 $APP_DIR ..."
    rm -rf "$APP_DIR"
    cp -r "$PROJECT_DIR" "$APP_DIR"
else
    echo "   项目已在目标目录 $APP_DIR"
fi

cd "$APP_DIR"

# ---------------------------
# 4. 创建 Python 虚拟环境 & 安装依赖
# ---------------------------
echo ""
echo "🐍 [4/8] 配置 Python 虚拟环境..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "   安装 Python 依赖..."
# 使用 pip 安装依赖时忽略已存在的
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 额外安装生产环境需要的包
pip install -q setproctitle

echo "   ✅ Python 环境配置完成"

# ---------------------------
# 5. 创建生产环境配置
# ---------------------------
echo ""
echo "🔑 [5/8] 配置环境变量..."

if [ ! -f ".env.production" ]; then
    if [ -f ".env" ]; then
        echo "   从 .env 复制配置文件..."
        cp .env .env.production
        # 添加 PRODUCTION 标志
        echo "PRODUCTION=true" >> .env.production
        echo "   ⚠️ 请记得编辑 .env.production 填写正确的 API 密钥！"
    else
        echo "   创建默认配置文件"
        echo "# AI智投量化平台 - 生产环境配置" > .env.production
        echo "DEEPSEEK_API_KEY=你的API密钥" >> .env.production
        echo "PRODUCTION=true" >> .env.production
        echo "   ⚠️ 请务必编辑 .env.production 填写 DeepSeek API 密钥！"
    fi
else
    echo "   配置文件已存在: .env.production"
fi

# 设置环境变量供 systemd 使用
echo "PRODUCTION=true" > /tmp/ai-quant-env

# ---------------------------
# 6. 构建前端（如果未构建）
# ---------------------------
echo ""
echo "🎨 [6/8] 检查前端构建..."

if [ ! -d "frontend/dist" ] || [ ! -f "frontend/dist/index.html" ]; then
    echo "   前端未构建，正在构建..."
    
    # 检查 Node.js
    if ! command -v node &>/dev/null; then
        echo "   安装 Node.js 18..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y -qq nodejs
    fi
    
    cd frontend
    echo "   安装前端依赖..."
    npm install --silent
    echo "   构建前端..."
    npm run build
    cd "$APP_DIR"
    echo "   ✅ 前端构建完成"
else
    echo "   前端已构建: frontend/dist/"
fi

# ---------------------------
# 7. 配置 nginx（可选，用于 80 端口转发）
# ---------------------------
echo ""
echo "🌐 [7/8] 配置 nginx 反向代理..."

cat > /etc/nginx/sites-available/ai-quant << 'NGINX_CONF'
server {
    listen 80;
    server_name _;

    # 禁止显示 nginx 版本号
    server_tokens off;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # 最大请求体（策略文件上传）
    client_max_body_size 10M;

    # 前端静态文件
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 60s;
    }

    # API 请求（超时时间加长，因为 AI 生成可能需要时间）
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    # WebSocket（如有需要）
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINX_CONF

# 启用站点
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
fi
ln -sf /etc/nginx/sites-available/ai-quant /etc/nginx/sites-enabled/

# 测试 nginx 配置
nginx -t && echo "   ✅ nginx 配置正确" || echo "   ⚠️ nginx 配置有误，请检查"

# 重启 nginx
systemctl restart nginx
systemctl enable nginx
echo "   ✅ nginx 已启动"

# ---------------------------
# 8. 配置 systemd 服务 & 启动
# ---------------------------
echo ""
echo "⚙️ [8/8] 配置系统服务..."

# 复制服务文件
cp deploy/ai-quant.service /etc/systemd/system/ai-quant.service

# 调整服务文件中的用户和路径
sed -i "s|WorkingDirectory=/var/www/ai-quant|WorkingDirectory=$APP_DIR|g" /etc/systemd/system/ai-quant.service
sed -i "s|EnvironmentFile=/var/www/ai-quant/.env.production|EnvironmentFile=$APP_DIR/.env.production|g" /etc/systemd/system/ai-quant.service
sed -i "s|User=www-data|User=root|g" /etc/systemd/system/ai-quant.service

# 设置正确的权限
chown -R root:root "$APP_DIR"
chmod -R 755 "$APP_DIR"

# 重新加载 systemd
systemctl daemon-reload

# 启动服务
systemctl enable ai-quant
systemctl restart ai-quant

# 等待服务启动
sleep 2

# 检查服务状态
if systemctl is-active --quiet ai-quant; then
    echo "   ✅ AI智投量化平台 服务运行中"
    echo ""
    echo "============================================"
    echo "  🎉 部署完成！"
    echo "============================================"
    echo ""
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo "  访问地址: http://$SERVER_IP"
    echo "  API文档:  http://$SERVER_IP/docs"
    echo ""
    echo "  管理命令:"
    echo "    sudo systemctl status ai-quant  # 查看状态"
    echo "    sudo systemctl restart ai-quant # 重启服务"
    echo "    sudo systemctl stop ai-quant    # 停止服务"
    echo "    sudo journalctl -u ai-quant -f  # 查看实时日志"
    echo ""
    echo "  ⚠️ 重要提醒:"
    echo "  1. 记得编辑 $APP_DIR/.env.production"
    echo "     填写 DeepSeek API 密钥"
    echo "  2. 重启服务生效:"
    echo "     sudo systemctl restart ai-quant"
    echo "  3. 如果无法访问，请检查云服务器"
    echo "     安全组/防火墙是否开放了 80 端口"
    echo ""
else
    echo "   ❌ 服务启动失败！查看日志:"
    systemctl status ai-quant --no-pager
    echo ""
    echo "   查看详细日志: sudo journalctl -u ai-quant -n 50 --no-pager"
fi
