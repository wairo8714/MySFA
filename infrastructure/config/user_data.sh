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

# Certbot インストール (Let's Encrypt)
yum install -y epel-release
yum install -y certbot

# ファイアウォール設定
systemctl start firewalld
systemctl enable firewalld
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload

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