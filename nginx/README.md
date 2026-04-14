# Nginx edge

Tout ce qui concerne l'edge Nginx local vit ici :

- `nginx.conf` : point d'entree principal charge par le conteneur
- `conf.d/edge.conf` : routage edge, rate limiting, headers et proxy vers backend/frontend
- `snippets/` : blocs reutilisables pour les pages d'erreur et autres directives partagees
- `errors/` : page d'erreur SSI et assets statiques associes

Montages Docker utilises par `docker-compose.yml` :

- `./nginx/nginx.conf` -> `/etc/nginx/nginx.conf`
- `./nginx/conf.d` -> `/etc/nginx/conf.d`
- `./nginx/snippets` -> `/etc/nginx/snippets`
- `./nginx/errors` -> `/usr/share/nginx/html/errors`
