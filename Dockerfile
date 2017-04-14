FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install -y  python3-pip
RUN apt-get install -y python-pip python-dev build-essential libfontconfig curl python-software-properties
RUN apt-get install -y yum screen
RUN apt-get install -y libcurl4-gnutls-dev librtmp-dev
RUN apt-get install -y nodejs npm
RUN ln -s /usr/bin/nodejs /usr/bin/node
RUN pip install --upgrade pip
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools

COPY . /app

RUN pip3 install -r app/requirements.txt

RUN export FLASK_APP=/app/application.py
RUN export FLASK_DEBUG=1
RUN export LC_ALL=C.UTF-8
RUN export LANG=C.UTF-8

ENTRYPOINT ["/bin/bash"]
