FROM traefik:v3.1

RUN apk add --no-cache openssl

COPY traefik.yml /etc/traefik/traefik.yml
COPY docker-entrypoint.sh /docker-entrypoint-dev.sh

RUN chmod +x /docker-entrypoint-dev.sh && \
    mkdir -p /etc/traefik/dynamic /certs

ENTRYPOINT ["/docker-entrypoint-dev.sh"]
