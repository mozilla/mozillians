""" Humans.txt generator, based on work done on Kuma.

https://github.com/mozilla/kuma/blob/master/apps/humans/models.py

More info about humans.txt here http://humanstxt.org/"""


from django.apps import AppConfig


default_app_config = 'mozillians.humans.HumansConfig'


class HumansConfig(AppConfig):
    name = 'mozillians.humans'
