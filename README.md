# Cabici

## Deployment

## Digital Ocean

Use docker to package the Django application.  

To build:
```
$ docker build -f Dockerfile -t docker.pkg.github.com/stevecassidy/races/web:latest . 
$ docker login docker.pkg.github.com -u stevecassidy -p <token>
$ docker push docker.pkg.github.com/stevecassidy/races/web:latest
```

On the host:

```
$ docker login docker.pkg.github.com -u stevecassidy -p <token>
$ docker pull docker.pkg.github.com/stevecassidy/races/web:latest
$ docker run -d --env-file env.prod -p 8000:8000  docker.pkg.github.com/stevecassidy/races/web:latest gunicorn --bind=0.0.0.0  races.wsgi
```

`.env.prod` contains the production configuration environment

Nginx installed on the Droplet routes traffic to the docker container.



Postgresql installed on the droplet serves the database.

Create database user with a password (under the postgres account):
```
$ createuser -P -s -e cabici
```

Create database (again as postgres):
```
createdb cabici
```

Restore database from backup (as root)
```
$ zcat cabici_pg-20201128.sql.gz | psql -U cabici -W --host=localhost
```

