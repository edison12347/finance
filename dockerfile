FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install -y python-pip python-pip3 python-dev build-essential libfontconfig curl python-software-properties
RUN pip3 install requirments.txt
COPY . /app

RUN export FLASK_APP=/app/application.py
RUN export FLASK_DEBUG=1

ENTRYPOINT ["/bin/bash"]