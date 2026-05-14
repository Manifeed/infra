# Nginx Edge

Everything related to the internal Nginx edge layer lives here.

Expected production-style flow:

`Client -> Traefik HTTPS/domain -> nginx internal HTTP -> public_api -> internal services`

Traefik owns TLS termination, HTTPS redirects, domain routing, and
normalization of `X-Forwarded-*` headers. `edge_nginx` is not exposed directly
on a host port in the default stack. Traefik is expected to reach
`edge_nginx:80` through the external Docker network
`${TRAEFIK_NETWORK_NAME:-traefik_proxy}`.

In local development, `infra/docker-compose.dev.yml` starts a dedicated
Traefik instance that generates a self-signed certificate for
`${TRAEFIK_DEV_HOST:-localhost}` and routes that hostname to `edge_nginx`.

- `nginx.conf`: main container entrypoint
- `conf.d/edge.conf`: routing, rate limits, security headers, and proxy rules
- `snippets/`: reusable shared directives
- `errors/`: SSI error page and static assets

Docker mounts used by `docker-compose.yml`:

- `./nginx/nginx.conf` -> `/etc/nginx/nginx.conf`
- `./nginx/conf.d` -> `/etc/nginx/conf.d`
- `./nginx/snippets` -> `/etc/nginx/snippets`
- `./nginx/errors` -> `/usr/share/nginx/html/errors`
