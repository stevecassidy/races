docker pull docker.pkg.github.com/stevecassidy/races/web:latest
docker stop cabici
docker rm cabici
docker run -d --env-file env.prod -p 8000:8000   --restart unless-stopped  --name cabici docker.pkg.github.com/stevecassidy/races/web:latest gunicorn -c ./gunicorn.config.py  races.wsgi