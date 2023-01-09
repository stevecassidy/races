# Cabici

## Deployment

## Digital Ocean

Use docker to package the Django application.  

To build:

```shell
docker build -f Dockerfile -t docker.pkg.github.com/stevecassidy/races/web:latest . 
docker login docker.pkg.github.com -u stevecassidy -p <token>
docker push docker.pkg.github.com/stevecassidy/races/web:latest
```

On the host:

```shell
docker login docker.pkg.github.com -u stevecassidy -p <token>
docker pull docker.pkg.github.com/stevecassidy/races/web:latest
docker run -d --env-file env.prod -p 8000:8000  docker.pkg.github.com/stevecassidy/races/web:latest gunicorn --bind=0.0.0.0  races.wsgi
```

`.env.prod` contains the production configuration environment

Nginx installed on the Droplet routes traffic to the docker container.

Postgresql installed on the droplet serves the database.

Create database user with a password (under the postgres account):

```shell
createuser -P -s -e cabici
```

Create database (again as postgres):

```shell
createdb cabici
```

Restore database from backup (as root)

```shell
zcat cabici_pg-20201128.sql.gz | psql -U cabici -W --host=localhost
```

## Running Tests

```shell
docker-compose run web python bin/production.py test
```

## Development under Docker Compose

Run under docker componse to get a postgres database.  

```shell
docker compose run -d
```

Should start web server on port 8000.

Restore database from backup into compose container:

```shell
docker compose exec -T db psql -U cabici -W --host=localhost < cabici_2023-01-01.Sunday.sql
```

