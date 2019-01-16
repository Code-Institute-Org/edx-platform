from django.conf.urls import patterns, url

urlpatterns = patterns(
    'challenges.views',

    url(r'^webhook', 'hello'),
)