from django.conf.urls.defaults import *
from django.views.generic import DetailView, ListView

urlpatterns = patterns('',
    (r'^(?:search)?$'      , 'domesday.views.search'),
    (r'^new$'              , 'domesday.views.new'),
    (r'^edit/(?P<pk>\d+)$' , 'domesday.views.edit'),
    (r'^view/(?P<pk>\d+)$' , 'domesday.views.view'),
    (r'^photo/(?P<pk>\d+)$', 'domesday.views.photo'),
    
    (r'^test$', 'domesday.views.test'),
)
