web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A config worker --loglevel=info --concurrency=2
beat: celery -A config beat --loglevel=info