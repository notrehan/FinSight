#!/bin/sh
set -eu
cd /app/backend
python manage.py migrate --noinput
exec "$@"
