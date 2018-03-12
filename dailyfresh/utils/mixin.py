from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import classonlymethod

# 重写as_view方法,返回登录验证
class LoginRequireView(View):
    @classonlymethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        return login_required(view)

# 通过多继承(__mor__集成顺序表)进行调用
class LoginRequireMixin(object):
   @classonlymethod
   def as_view(cls,**initkwargs):
       view = super().as_view(**initkwargs)
       return login_required(view)