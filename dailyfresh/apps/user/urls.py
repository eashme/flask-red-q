from django.conf.urls import url
from apps.user import views

urlpatterns = [
    url(r"^register$", views.RegisterView.as_view(),name='register'),
    url(r'^active$', views.ActiveView.as_view(),name='active'),
    url(r'^login$',views.LoginView.as_view(),name='login'),
    url('^loginout$',views.LoginOutView.as_view(),name="loginout"),

    #  -----用户中心-----
    url(r'^user$',views.UserView.as_view(),name='user'),
    url(r'^order$', views.UserOrderView.as_view(),name='order'),
    url(r'^address', views.AddressView.as_view(),name='address'),
    url(r'^defautl_addr$',views.DefaultAddrView.as_view(),name='default_addr')
]
