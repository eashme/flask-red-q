from django.shortcuts import render,redirect
from django.views.generic import View
from django.core.urlresolvers import reverse
from apps.user.models import User,Address
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from celery_task.tasks import send_register_active_email
from django.conf import settings
from itsdangerous import SignatureExpired
from django.http import HttpResponse
from django.contrib.auth import login,logout,authenticate
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from utils.mixin import LoginRequireView,LoginRequireMixin
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
from apps.order.models import OrderGoods,OrderInfo
import re
# Create your views here.

class RegisterView(View):
    def get(self,request):
        """访问注册"""
        return render(request, "register.html")

    def post(self,request):
        """用户注册验证"""

        user_name = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')

        # 检测信息是否完整
        if not all([user_name,password,email]):
            return render(request, 'register.html', {'errmsg': '注册信息不完整'})

        # 检测邮箱是否符合规则
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
            return render(request, "register.html", {'errmsg': '邮箱格式错误'})

        # 检测用户名是否已存在
        try:
            user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            user = None

        if user is not None:
            return render(request, "register.html", {'errmsg': '用户名已存在'})

        # 检测密码是否包含于用户名中
        if password in user_name or user_name in password:
            return render(request, "register.html", {'errmsg': '用户名与密码不要互相包含'})

        # 使用内置的create_user对用户进行注册
        user = User.objects.create_user(user_name,email,password)
        # 是否激活设置为初始的false
        user.is_active = 0
        user.save()

        # 发送用户id进行激活
        info = {'user_id':user.id}
        # 实例化serializer加密工具,设置秘钥为setting文件的SECRET_KEY,过期时间为1小时
        serializer = Serializer(settings.SECRET_KEY, 3600)
        # 加密用户id
        token = serializer.dumps(info, salt=settings.SECRET_KEY).decode()

        # 加入celery任务，传入email发送目标email,用户名,加密后的用户id
        send_register_active_email.delay(email,user_name,token)

        return redirect(reverse('goods:index'))

class ActiveView(View):
    def get(self,request):
        """用户激活"""
        token = request.GET.get('token')

        # 解密,拿到用户id
        serializer = Serializer(settings.SECRET_KEY,3600)
        try:
            info = serializer.loads(token,salt=settings.SECRET_KEY)
        except SignatureExpired:
            return HttpResponse("邮件已超1小时的有效期,请重新申请激活")
        user_id = info['user_id']
        # 拿到要激活的用户
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponse("出来混不容易,别攻击啊兄弟")
        # 用户激活操作
        user.is_active = 1
        user.save()
        return redirect(reverse('goods:index'))

class LoginView(View):
    def get(self,request):
        """登录界面"""
        user_name = request.COOKIES.get('username')
        checked  = 'checked'

        if user_name is None:
            checked = ''
            user_name = ''

        return render(request, "login.html", {'username':user_name, 'checked':checked})

    def post(self,request):
        """登录处理"""
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remeber = request.POST.get('remeber')

        # 检验完整性
        if not all([username,password]):
            return render(request, "login.html", {'errmsg': '请输入完整信息登录'})

        # 检查用户名密码是否错误
        user = authenticate(username=username,password=password)
        if user is not None:
            # the password verified for the user
            if user.is_active:
                # 已经激活

                # 记录登录状态
                login(request,user)
                # 取得之前用户访问的页面url
                next_url = request.GET.get('next',reverse('goods:index'))
                # 记录重定向response对象
                response = redirect(next_url)
                # 设置cookie保存登录过的用户名
                if remeber == 'on':
                    response.set_cookie('username',username,3600*24*30)
                else:
                    response.delete_cookie('remeber')

                return response
            else:
                # 还没激活
                return render(request, 'login.html', {"errmsg": '请先激活您的账号'})
        else:
            # 账号或密码错误
            return render(request, 'login.html', {'errmsg': '账号或者密码错误'})

# /user/loginout
class LoginOutView(View):
    """登出"""
    def get(self,request):
        logout(request)
        return redirect(reverse('user:login'))

# /user/user
# class UserView(LoginRequireView): #     重写as_view方法
class UserView(LoginRequireMixin, View):  # 多继承(mro继承顺序表)方法
    def get(self,request):
        # from redis import StrictRedis         # 导入redis的包
        # conn = StrictRedis(host='127.0.0.1',port=6397,db=4)  # 和redis数据库建立链接
        conn = get_redis_connection('default')  # 使用setting文件中的’default‘配置,启动redis数据库
        user_id = request.user.id
        history_key = 'history_%d' % user_id
        history_list =  conn.lrange(history_key,0,4)
        skus = []
        # 通过历史记录查询到的id来取得商品SKU对象加入到skus列表
        for sku_id in history_list:
            skus.append(GoodsSKU.objects.get(id=sku_id))
        # 传入context至模板中
        context = {
            'page': 'user',
            'skus': skus
        }

        return render(request, 'user_center_info.html', context)

# /user/order
# class UserOrderView(LoginRequireView): #     重写as_view方法
class UserOrderView(LoginRequireMixin, View):  # 多继承(mro继承顺序表)方法
    def get(self,request,page_no):
        """显示用户订单界面"""
        try:
            page_no = int(page_no)
        except Exception:
            page_no = 1

        # 拿到该用户所有的订单信息
        orders = OrderInfo.objects.filter(user=request.user)

        for order in orders:
            # 拿到各个订单中对应的商品,
            order.order_goods = OrderGoods.objects.filter(order=order)
            # 实际付款
            order.total_amount = order.total_price
            # 小计价格
            for goods in order.order_goods:
                goods.goods_price = round(goods.price * goods.count, 2)
            # 支付状态数字替换文字
            order.order_status = OrderInfo.ORDER_STATUS[order.order_status]

        # 生成分页对象
        paginator = Paginator(orders, 2)

        if page_no < 1 or page_no > paginator.num_pages:
            page_no = 1

        page = paginator.page(page_no)

        # 页码处理
        # 如果分页之后页码超过5页，最多在页面上只显示5个页码：当前页前2页，当前页，当前页后2页
        # 1) 分页页码小于5页，显示全部页码
        if paginator.num_pages < 5:
            pages = range(1, paginator.num_pages + 1)
        # 2）当前页属于1-3页，显示1-5页
        elif page.number < 4:
            pages = range(1, 6)
        # 3) 当前页属于后3页，显示后5页
        elif page.number > paginator.num_pages - 3:
            pages = range(paginator.num_pages - 4, paginator.num_pages + 1)
        # 4) 其他请求，显示当前页前2页，当前页，当前页后2页
        else:
            pages = range(page.number - 2, page.number + 3)

        if len(page) == 0 : pages = []

        return render(request,'user_center_order.html',{'page':'order','page_set':page,'page_list' : pages})

# /user/address
# class AddressView(LoginRequireView): #     重写as_view方法
class AddressView(LoginRequireMixin,View): #  多继承(mro继承顺序表)方法
    def get(self, request):
        addr = Address.objects.filter(user=request.user)
        addr_list = []
        for address in addr:
            if address.is_default:
                addr_list.insert(0,address)
            else:
                addr_list.append(address)

        context = {
            'address' :  addr_list,
            'page': 'address'
        }
        return render(request, 'user_center_site.html',context)

    def post(self,request):
        receiver = request.POST.get('receiver')
        address = request.POST.get('address_info')
        zip_code = request.POST.get('zip_code')
        tel_number = request.POST.get('tel_number')

        addr = Address.objects.get_default_addr(request.user)

        if addr is not None:
            is_default = False
        else:
            is_default = True
        Address.objects.create(user=request.user
                               ,receiver=receiver
                               ,addr=address
                               ,zip_code=zip_code
                               ,phone=tel_number
                               ,is_default=is_default)

        return redirect(reverse('user:address'))

# /defautl_addr
class DefaultAddrView(LoginRequireMixin,View):
    """设置默认收货地址"""
    def get(self,request):
        addr_id = request.GET.get('addr_id')
        # 将其他的地址设为非默认地址
        other_addr = Address.objects.filter(is_default=True)
        for addr in other_addr:
            addr.is_default = False
            addr.save()

        address = Address.objects.get(id=addr_id)
        address.is_default = True
        address.save()

        return redirect(reverse('user:address'))