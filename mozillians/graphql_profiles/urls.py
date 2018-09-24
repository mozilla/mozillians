from django.conf import settings
from django.conf.urls import url

from mozillians.graphql_profiles import views

app_name = 'graphql_profiles'
urlpatterns = [
    # App level graphQL url
    url(r'^$', views.MozilliansGraphQLView.as_view(graphiql=settings.DEV), name='graphql_view'),
]
