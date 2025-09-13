#!/bin/bash

# ログ設定
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=== MySFA セットアップ開始 ==="

# システム更新
yum update -y

# Docker インストール
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Docker Compose インストール
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Nginx インストール
yum install -y nginx
systemctl start nginx
systemctl enable nginx

# Certbot インストール (Let's Encrypt)
yum install -y epel-release
yum install -y certbot python3-certbot-nginx

# ファイアウォール設定
systemctl start firewalld
systemctl enable firewalld
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload

# アプリケーション設定
cat > /home/ec2-user/docker-compose.yml << EOF
version: '3.8'

services:
  app:
    image: ${dockerhub_username}/mysfa_ver2:latest
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./src:/app
    environment:
      - MYSQL_HOST=db
      - MYSQL_PORT=3306
      - MYSQL_DATABASE=${mysql_database}
      - MYSQL_USER=${mysql_user}
      - MYSQL_PASSWORD=${mysql_password}
      - SECRET_KEY=${secret_key}
      - DEBUG=False
      - ALLOWED_HOSTS=${allowed_hosts}
    depends_on:
      - db
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=${mysql_root_password}
      - MYSQL_USER=${mysql_user}
      - MYSQL_PASSWORD=${mysql_password}
      - MYSQL_DATABASE=${mysql_database}
    ports:
      - "127.0.0.1:3306:3306"
    volumes:
      - db_data:/var/lib/mysql
    restart: unless-stopped
    command: --default-authentication-plugin=mysql_native_password

volumes:
  db_data:
EOF

# Nginx設定
cat > /etc/nginx/conf.d/mysfa.conf << EOF
server {
    listen 80;
    server_name ${domain_name} $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4);
    
    # HTTP to HTTPS redirect
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${domain_name} $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4);
    
    # SSL configuration (Let's Encrypt certificates)
    ssl_certificate /etc/letsencrypt/live/${domain_name}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${domain_name}/privkey.pem;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # Static files caching
    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files caching
    location /media/ {
        proxy_pass http://127.0.0.1:8000/media/;
        expires 1M;
        add_header Cache-Control "public";
    }
    
    # Health check endpoint
    location /health/ {
        proxy_pass http://127.0.0.1:8000/health/;
        access_log off;
    }
}
EOF

# アプリケーション起動
cd /home/ec2-user
docker-compose up -d

# データベースの初期化待機
echo "データベースの初期化を待機中..."
sleep 30

# データベースマイグレーション
echo "データベースマイグレーションを実行中..."
docker-compose exec -T app python manage.py migrate

# アプリケーション起動待機
echo "アプリケーション起動を待機中..."
sleep 30

# Nginx設定テスト
nginx -t

# Nginx再起動
systemctl restart nginx

# SSL証明書取得（ドメインが設定されている場合）
if [ "${domain_name}" != "mysfa.net" ]; then
    echo "SSL証明書を取得中..."
    certbot --nginx -d ${domain_name} --non-interactive --agree-tos --email admin@${domain_name}
    systemctl reload nginx
fi

# ログローテーション設定
cat > /etc/logrotate.d/mysfa << EOF
/var/log/user-data.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 root root
}
EOF

echo "=== MySFA セットアップ完了 ==="
echo "アプリケーションURL: https://${domain_name}"
echo "IPアドレス: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
