# pull official base image
FROM python:3.8.3-alpine

## install build dependencies
RUN apk add build-base libffi-dev openssl-dev postgresql-dev python3-dev musl-dev curl
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"


# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
# 
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install cryptography

RUN pip install -r requirements.txt

# copy project
COPY . .

RUN python bin/production.py collectstatic
