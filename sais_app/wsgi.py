"""
WSGI config for sais_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sais_app.settings")

application = get_wsgi_application()
app = application

if os.environ.get("VERCEL"):
    from django.core.management import call_command
    try:
        call_command("migrate", interactive=False)
        call_command("seed_songs")
    except Exception as e:
        print("Vercel startup init notice:", e)


