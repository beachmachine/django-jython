from django.core.handlers import wsgi
import os

def handler(environ, start_response):
    os.putenv("DJANGO_SETTINGS_MODULE", "%(settings_module)s")
    h = wsgi.WSGIHandler()
    return h(environ, start_response)
