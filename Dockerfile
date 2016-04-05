FROM python:2.7.10
ADD . /code
WORKDIR /code
RUN apt-get update && apt-get install -y mysql-client node-less
RUN ./peep.sh install -r requirements/dev.txt