from django.conf.urls import url

from mozillians.graphql import views

app_name = 'graphql'
urlpatterns = [
    # App level graphQL url
    url(r'^$', views.MozilliansGraphQLView.as_view(graphiql=True), name='graphql_view'),
]
