#!/bin/sh
set -e

python init_db.py

exec gunicorn \
    --workers=4 \
    --worker-class=sync \
    --bind=0.0.0.0:5000 \
    --timeout=120 \
    --access-logfile=- \
    --error-logfile=- \
    "app:create_app()"