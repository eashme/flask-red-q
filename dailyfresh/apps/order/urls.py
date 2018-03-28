from django.conf.urls import url
from apps.order.views import OrderPlace,OrderCommitView,AliPayOrder

urlpatterns = [
    url(r'^$', OrderPlace.as_view(),name='place'),
    url(r'^commit$', OrderCommitView.as_view(),name='commit'),
    url(r'^pay$',AliPayOrder.as_view(),name='pay'),
]
