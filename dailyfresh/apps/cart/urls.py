from django.conf.urls import url
from apps.cart.views import CartList,UpdateCart

urlpatterns = [
    url(r'^$',CartList.as_view(),name='cart_list'),
    url(r'update',UpdateCart.as_view(),name='update_cart'),
]
