from django.conf.urls import url

from mozillians.graphql_profiles import views

app_name = 'graphql_profiles'
urlpatterns = [
    # App level graphQL url
    url(r'^$', views.MozilliansGraphQLView.as_view(graphiql=True), name='graphql_view'),
]
