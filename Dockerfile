FROM python:2.7
ADD . /code
WORKDIR /code
RUN apt-get update
RUN apt-get install -y mysql-client node-less
RUN ./peep.sh install -r requirements/dev.txt