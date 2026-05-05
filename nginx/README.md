# Nginx edge

Tout ce qui concerne l'edge Nginx interne vit ici. En production, le flux attendu est :

`Client -> Traefik HTTPS/domain -> nginx HTTP interne -> public_api -> services internes`

Traefik termine TLS, force HTTPS, choisit le domaine et nettoie/pose les headers
`X-Forwarded-*`. Le compose principal ne publie plus nginx sur un port hote :
Traefik doit joindre `edge_nginx:80` via le reseau Docker externe
`${TRAEFIK_NETWORK_NAME:-traefik_proxy}`.

En dev, `infra/docker-compose.dev.yml` lance un Traefik local qui genere un
certificat autosigne pour `${TRAEFIK_DEV_HOST:-localhost}` et route ce host vers
`edge_nginx`.

- `nginx.conf` : point d'entree principal charge par le conteneur
- `conf.d/edge.conf` : routage edge, rate limiting, headers et proxy vers backend/frontend
- `snippets/` : blocs reutilisables pour les pages d'erreur et autres directives partagees
- `errors/` : page d'erreur SSI et assets statiques associes

Montages Docker utilises par `docker-compose.yml` :

- `./nginx/nginx.conf` -> `/etc/nginx/nginx.conf`
- `./nginx/conf.d` -> `/etc/nginx/conf.d`
- `./nginx/snippets` -> `/etc/nginx/snippets`
- `./nginx/errors` -> `/usr/share/nginx/html/errors`
