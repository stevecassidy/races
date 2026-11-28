# pull official base image
FROM python:3.11-slim

# install build dependencies
# (gcc + libpq-dev needed for psycopg2 binary compilation; other deps have wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip

# copy project
COPY . .

RUN pip install -r requirements.txt

RUN python bin/production.py collectstatic
