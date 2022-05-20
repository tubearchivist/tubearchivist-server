#!/usr/bin/env bash

mkdir -p "/data/hooks"
uwsgi --ini uwsgi.ini
