FROM python:3.10.4-slim-bullseye

RUN apt-get clean && apt-get -y update && \
    apt-get -y install --no-install-recommends \
    build-essential libpq-dev vim htop bmon net-tools iputils-ping procps

ENV PATH=/root/.local/bin:$PATH
COPY requirements.txt /requirements.txt
RUN pip install --user -r requirements.txt

RUN mkdir /data

COPY . /srv/flask_app
WORKDIR /srv/flask_app

RUN chmod +x ./start.sh

VOLUME /data
CMD ["./start.sh"]
