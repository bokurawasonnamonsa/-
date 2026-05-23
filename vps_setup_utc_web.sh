#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/utc_web"
ZIP_PATH="/tmp/utc_web.zip"
DOMAIN="${UTC_DEPLOY_DOMAIN:-3301-svs.jp}"
SSL_DIR="/etc/nginx/ssl"
SELF_CERT="${SSL_DIR}/utc_origin.pem"
SELF_KEY="${SSL_DIR}/utc_origin.key"
LE_CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
LE_KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"

export DEBIAN_FRONTEND=noninteractive
apt update
apt -y upgrade
apt -y install python3 python3-venv python3-pip nginx unzip ufw certbot python3-certbot-nginx openssl

ufw allow OpenSSH || true
ufw allow 80 || true
ufw allow 443 || true
ufw --force enable || true

mkdir -p "${APP_DIR}"
mkdir -p /var/www/certbot/.well-known/acme-challenge
mkdir -p "${SSL_DIR}"

cd "${APP_DIR}"
unzip -o "${ZIP_PATH}"

rm -f "${APP_DIR}/vps_deploy_local.secret" "${APP_DIR}/cloudflare_dns_config.ps1" || true

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi "uvicorn[standard]" websockets wsproto

cat >/etc/systemd/system/utc-web.service <<'EOF'
[Unit]
Description=UTC Web FastAPI
After=network.target

[Service]
User=root
WorkingDirectory=/opt/utc_web
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/utc_web/.venv/bin/python /opt/utc_web/main.py
Restart=always
RestartSec=2
StartLimitIntervalSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable utc-web
systemctl restart utc-web

ensure_self_signed_origin() {
  if [[ -f "$SELF_CERT" && -f "$SELF_KEY" ]]; then
    return 0
  fi
  openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
    -keyout "$SELF_KEY" \
    -out "$SELF_CERT" \
    -subj "/CN=${DOMAIN}" \
    -addext "subjectAltName=DNS:${DOMAIN}"
  chmod 640 "$SELF_KEY" || true
}

# $ACTIVE_CERT / $ACTIVE_KEY = PEM paths for nginx :443 (Let's Encrypt or self-signed fallback)
write_utc_nginx() {
  local cert="$1"
  local key="$2"
  local site="/etc/nginx/sites-available/utc_web"
  {
    cat <<'MAPFIX'
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

MAPFIX
    cat <<HTTP80
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_buffering off;
        proxy_connect_timeout 60s;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}

HTTP80
    cat <<SSLTOP
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${DOMAIN};

    ssl_certificate ${cert};
    ssl_certificate_key ${key};

SSLTOP
    if [[ -f /etc/letsencrypt/options-ssl-nginx.conf ]]; then
      echo "    include /etc/letsencrypt/options-ssl-nginx.conf;"
    else
      echo "    ssl_protocols TLSv1.2 TLSv1.3;"
    fi
    if [[ -f /etc/letsencrypt/ssl-dhparams.pem ]]; then
      echo "    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;"
    fi
    cat <<'SSLLOC'
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_buffering off;
        proxy_connect_timeout 60s;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}

SSLLOC
  } >"$site"
}

ensure_self_signed_origin
write_utc_nginx "$SELF_CERT" "$SELF_KEY"
ln -sf /etc/nginx/sites-available/utc_web /etc/nginx/sites-enabled/utc_web
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

if certbot certonly \
  --webroot -w /var/www/certbot \
  -d "${DOMAIN}" \
  --non-interactive \
  --agree-tos \
  --register-unsafely-without-email \
  --keep-until-expiring \
  ; then
  write_utc_nginx "$LE_CERT" "$LE_KEY"
  nginx -t
  systemctl reload nginx || systemctl restart nginx
  echo "TLS: Let's Encrypt OK for ${DOMAIN}"
else
  echo "CERTBOT failed (Cloudflare プロキシ配下ではよくある)。自己署名で :443 を継続します。"
  echo "Cloudflare SSL/TLS は「フル（厳密でない）」にするとオリジン自己署名で接続できます。"
  ensure_self_signed_origin
  write_utc_nginx "$SELF_CERT" "$SELF_KEY"
  nginx -t
  systemctl restart nginx
fi

echo "=== DONE ==="
echo "UTC app deployed on VPS."
echo "Cloudflare: SSL/TLS = フル（厳密でない）推奨。厳密モードはオリジンに Let's Encrypt 等の正規証明書が必要です。"
