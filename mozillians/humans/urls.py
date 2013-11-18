from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    'mozillians.humans',
    url(r'^humans.txt$', 'views.humans', name='humans')
)
