FROM python:2.7
ADD . /code
WORKDIR /code
RUN apt-get update && apt-get install -y mysql-client node-less
RUN pip install -r requirements/compiled.txt
