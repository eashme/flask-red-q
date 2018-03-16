from django.conf.urls import url
from apps.cart.views import CartList,UpdateCart,AddCart,DelCart

urlpatterns = [
    url(r'^$',CartList.as_view(),name='cart_list'),
    url(r'^update$',UpdateCart.as_view(),name='update_cart'),
    url(r'^add$',AddCart.as_view(),name='add_cart'),
    url(r'^del$',DelCart.as_view(),name='del_cart'),
]
