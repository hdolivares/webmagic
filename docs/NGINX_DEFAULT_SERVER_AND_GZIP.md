# Nginx: default server hardening and gzip

Apply these on the server to reduce bandwidth from bot traffic and compress responses. Version-controlled so changes are reproducible.

## 1. Harden the default server (port 80)

The **default** server catches requests by IP or unknown `Host`. That traffic is often bots/scanners and consumes bandwidth. Prefer to close the connection without responding.

On the server, edit the default server block (e.g. `/etc/nginx/sites-available/default`). Replace or add a `server` block that listens as `default_server` and returns 444 (close connection):

```nginx
# Default server: drop requests by IP or unknown Host (reduces bot traffic and bandwidth)
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 444;
}
```

If your distro’s default file already has a `server { listen 80 default_server; ... }` block, change its `location /` (or root) to simply `return 444;` so no response body is sent.

Reload nginx after editing:

```bash
nginx -t && systemctl reload nginx
```

## 2. Enable gzip

In the **main** nginx config (e.g. `/etc/nginx/nginx.conf`), inside the `http { ... }` block, enable gzip and set types. Often `gzip on;` is commented out — uncomment and add:

```nginx
http {
    # ... existing directives ...

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml;
}
```

Reload nginx after editing:

```bash
nginx -t && systemctl reload nginx
```

These changes are server-only; keep a copy of the modified config (or this doc) in version control so you can reapply after server changes.
