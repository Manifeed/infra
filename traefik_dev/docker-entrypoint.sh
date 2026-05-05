#!/bin/sh
set -eu

CERT_DIR=/certs
DYNAMIC_DIR=/etc/traefik/dynamic
DEV_HOST="${TRAEFIK_DEV_HOST:-localhost}"
DEV_DASHBOARD_HOST="${TRAEFIK_DEV_DASHBOARD_HOST:-traefik.localhost}"
CERT_FILE="$CERT_DIR/$DEV_HOST.crt"
KEY_FILE="$CERT_DIR/$DEV_HOST.key"
OPENSSL_CONFIG="$(mktemp)"

cleanup() {
  rm -f "$OPENSSL_CONFIG"
}

trap cleanup EXIT

mkdir -p "$CERT_DIR" "$DYNAMIC_DIR"

if [ ! -s "$CERT_FILE" ] || [ ! -s "$KEY_FILE" ]; then
  cat >"$OPENSSL_CONFIG" <<EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = $DEV_HOST

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DEV_HOST
DNS.2 = localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

  openssl req \
    -x509 \
    -nodes \
    -days "${TRAEFIK_DEV_CERT_DAYS:-825}" \
    -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -config "$OPENSSL_CONFIG"
fi

cat >"$DYNAMIC_DIR/tls.yml" <<EOF
tls:
  stores:
    default:
      defaultCertificate:
        certFile: $CERT_FILE
        keyFile: $KEY_FILE
  certificates:
    - certFile: $CERT_FILE
      keyFile: $KEY_FILE
http:
  routers:
    manifeed-edge-http:
      rule: Host(\`$DEV_HOST\`)
      entryPoints:
        - web
      middlewares:
        - manifeed-https-redirect
      service: manifeed-edge
    manifeed-edge-https:
      rule: Host(\`$DEV_HOST\`)
      entryPoints:
        - websecure
      tls: {}
      service: manifeed-edge
    traefik-dev-dashboard:
      rule: Host(\`$DEV_DASHBOARD_HOST\`)
      entryPoints:
        - websecure
      tls: {}
      service: api@internal
  middlewares:
    manifeed-https-redirect:
      redirectScheme:
        scheme: https
  services:
    manifeed-edge:
      loadBalancer:
        servers:
          - url: http://edge_nginx:80
EOF

exec traefik --configFile=/etc/traefik/traefik.yml
