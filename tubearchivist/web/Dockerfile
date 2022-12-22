# builder
FROM python:3.10.8-slim-bullseye as builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential

COPY requirements.txt /requirements.txt
RUN pip install --user -r requirements.txt

# final
FROM python:3.10.8-slim-bullseye as tubearchivist-web

ARG INSTALL_DEBUG
ENV PYTHONUNBUFFERED 1

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

RUN if [ "$INSTALL_DEBUG" ] ; then \
        apt-get -y update && apt-get -y install --no-install-recommends \
        vim htop bmon net-tools iputils-ping procps \
        && pip install --user ipython \
    ; fi

RUN mkdir /data

COPY . /srv/flask_app
WORKDIR /srv/flask_app

RUN chmod +x ./start.sh

VOLUME /data
CMD ["./start.sh"]
