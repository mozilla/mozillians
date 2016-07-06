FROM python:2.7.10
ADD . /code
WORKDIR /code
RUN apt-get update && apt-get install -y mysql-client node-less gettext && \
    pip install --upgrade pip==8.0.3
RUN pip install --require-hashes --no-deps -r requirements/dev.txt
