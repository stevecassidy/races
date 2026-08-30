# pull official base image
FROM python:3.14-alpine

## install build dependencies
RUN apk add --no-cache build-base libffi-dev openssl-dev postgresql-dev python3-dev musl-dev curl

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install dependencies
RUN python -m pip install --upgrade pip "setuptools<81" wheel

# copy project
COPY . .

RUN python -m pip install -r requirements.txt
RUN python -m pip install --upgrade "setuptools<81"

# Runtime-only Django commands are run from docker-compose so they can use the
# container environment and settings.
