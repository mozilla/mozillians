FROM python:3.4.3
EXPOSE 8080
ADD . /code
WORKDIR /code
RUN apt-get update && apt-get install -y mysql-client node-less && \
    pip install --upgrade pip==8.1.2
RUN pip install --require-hashes --no-deps -r requirements/dev.txt
