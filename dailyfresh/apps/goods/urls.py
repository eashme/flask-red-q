from django.conf.urls import url
from apps.goods import views
urlpatterns = [
    url(r'^detail$',views.DetailView.as_view(),name='detail'),







    url(r'^',views.IndexView.as_view(),name="index"),
]
