$env:DJANGO_SETTINGS_MODULE="config.settings.production"
$env:SECRET_KEY="super-secret"
$env:ALLOWED_HOSTS="127.0.0.1,localhost"
python manage.py runserver
