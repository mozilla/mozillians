FROM python:2.7
ADD . /code
WORKDIR /code
RUN apt-get update
RUN apt-get install -y mysql-client node-less
RUN pip install -r requirements/compiled.txt
RUN pip install -r requirements/dev.txt
RUN pip install -r requirements/prod.txt