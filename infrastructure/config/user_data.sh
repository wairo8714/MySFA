# nginx.conf作成（既存のディレクトリ/ファイルを削除してから作成）
rm -rf /home/ec2-user/nginx.conf || true
cat > /home/ec2-user/nginx.conf << 'NGINX_EOF'
server {
    listen 80;
    server_name ${domain_name};
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${domain_name};

    ssl_certificate /etc/letsencrypt/live/${domain_name}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${domain_name}/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    location /static/ {
        proxy_pass http://app:8000/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        proxy_pass http://app:8000/media/;
        expires 1M;
        add_header Cache-Control "public";
    }

    location /health/ {
        proxy_pass http://app:8000/health/;
        access_log off;
    }
}
NGINX_EOF

# ドメイン名を置換
sed -i "s/\${domain_name}/${domain_name}/g" /home/ec2-user/nginx.conf

# 所有者とパーミッションを設定
chown ec2-user:ec2-user /home/ec2-user/nginx.conf
chmod 644 /home/ec2-user/nginx.conf