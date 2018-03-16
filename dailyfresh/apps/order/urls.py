from django.conf.urls import url
from apps.order.views import OrderPlace,OrderCommitView

urlpatterns = [
    url(r'^$', OrderPlace.as_view(),name='place'),
    url(r'^commit$', OrderCommitView.as_view(),name='commit'),
]
