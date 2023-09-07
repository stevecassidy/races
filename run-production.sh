docker pull waratahmasters/races:latest
docker stop cabici
docker rm cabici
docker run -d --env-file env.prod -p 8000:8000   --restart unless-stopped  --name cabici waratahmasters/races:latest gunicorn -c ./gunicorn.config.py  races.wsgi