from django.core.handlers import wsgi
import os

def handler(environ, start_response):
    os.putenv("DJANGO_SETTINGS_MODULE", "{{ settings.SETTINGS_MODULE }}")
    h = wsgi.WSGIHandler()
    return h(environ, start_response)
