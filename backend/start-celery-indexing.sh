#!/bin/sh
exec celery -A celery_app worker \
  --loglevel=info \
  --concurrency="${CELERY_WORKER_CONCURRENCY:-4}" \
  -Q celery \
  -n indexing@%h
