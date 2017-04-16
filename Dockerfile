FROM tiangolo/uwsgi-nginx-flask:flask-python3.5

RUN apt-get update -y && apt-get install -y python-pip python3-pip python-dev\
											build-essential libfontconfig curl python-software-properties\
                                        	yum screen libcurl4-gnutls-dev librtmp-dev nodejs npm
RUN pip3 install --upgrade pip && pip3 install --upgrade setuptools
RUN ln -s /usr/bin/nodejs /usr/bin/node

COPY . /app

RUN pip3 install -r /app/requirements.txt

ENV FLASK_APP=/app/main.py
ENV FLASK_DEBUG=1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8