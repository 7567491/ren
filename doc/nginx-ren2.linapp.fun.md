# ren2.linapp.fun Nginx 配置（通配符 SSL）

基于 `frontend/` 极简静态首页，使用 `*.linapp.fun` 证书与 18005 后端，保持与 `ren.linapp.fun` 相同的反代规则。

## 约定
- 前端静态目录：`/home/ren/frontend/dist`（先执行 `npm run build`）
- 后端服务：`http://127.0.0.1:18005`
- 证书路径：`/etc/letsencrypt/live/linapp.fun/fullchain.pem` 与 `privkey.pem`（通配符 `*.linapp.fun`）

## 配置示例
```
server {
    listen 80;
    server_name ren2.linapp.fun;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ren2.linapp.fun;

    ssl_certificate /etc/letsencrypt/live/linapp.fun/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/linapp.fun/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;

    root /home/ren/frontend/dist;
    index index.html;
    client_max_body_size 200m;

    location /api/ {
        proxy_pass http://127.0.0.1:18005/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location /output/ {
        alias /home/ren/output/;
        add_header Access-Control-Allow-Origin *;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 启用步骤
1. 将上方配置保存到 `/etc/nginx/sites-available/ren2.linapp.fun`。
2. 软链启用：`sudo ln -s /etc/nginx/sites-available/ren2.linapp.fun /etc/nginx/sites-enabled/`。
3. 校验并重载：`sudo nginx -t && sudo systemctl reload nginx`。
4. 访问 `https://ren2.linapp.fun/` 验证首页加载，`/api/health` 确认后端连通。
