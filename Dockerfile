# pull official base image
FROM python:3.14-alpine

## install build dependencies
RUN apk add --no-cache build-base libffi-dev openssl-dev postgresql-dev python3-dev musl-dev curl

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install runtime dependencies only - the development tooling (debug toolbar,
# vcrpy, black, ruff, mypy, coverage) lives in requirements/dev.txt and has no
# place in the deployed image
RUN python -m pip install --upgrade pip
COPY requirements/ requirements/
RUN python -m pip install -r requirements/production.txt

# copy project
COPY . .

# Runtime-only Django commands are run from docker-compose so they can use the
# container environment and settings.
