# pull official base image
FROM python:3.8.3-alpine

## install build dependencies
RUN apk add build-base libffi-dev openssl-dev postgresql-dev

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .

RUN python bin/production.py collectstatic
