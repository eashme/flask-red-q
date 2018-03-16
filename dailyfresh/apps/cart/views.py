from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import View
from django_redis import get_redis_connection
from utils.mixin import LoginRequireMixin
from apps.goods.models import GoodsSKU

# Create your views here.

class CartList(LoginRequireMixin,View):
    def get(self,request):
        """显示购物车的列表页面"""
        # 获取redis链接，准备操作redis数据库取出购物车中的商品编号
        conn = get_redis_connection('default')

        # 拼接出登陆的用户的键
        cart_key = 'cart_%d' % request.user.id

        # hgetall(key)取出所有的键值对，返回字典
        dict_cart = conn.hgetall(cart_key)
        skus = []
        totalamount = 0
        totalcount = 0
        for sku_id,count in dict_cart.items():
            # 通过商品id拿到商品的对象
            sku = GoodsSKU.objects.get(id=sku_id)
            # 解码
            count = int(count.decode())
            # 将所有商品对象和数量保存起来
            skus.append((sku,count))
            totalamount += (sku.price * count)
            totalcount += count

        return render(request,'cart.html',{
            'skus' : skus,
            'totalamount' : totalamount,
            'totalcount' : totalcount,
        })

# /cart/add
class AddCart(View):
    # 添加购物车
    def post(self,request):
        if not request.user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录去'})

        count = request.POST.get('sku_count')
        sku_id = request.POST.get('sku_id')

        if not all([count, sku_id]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 校验商品数量count
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '商品数量必须为有效数字'})

        # 链接redis数据库
        conn = get_redis_connection('default')
        # 拼接key值
        cart_key = 'cart_%d' % request.user.id

        old_count = conn.hget(cart_key, sku_id)

        if old_count:
            # 如果购物车中已经存在该商品就增加数量
            old_count = count + int(old_count)
        else:
            # 不存在就赋值
            old_count = count

        print(old_count)

        if old_count > sku.stock:
            return JsonResponse({'res':4,'errmsg':'库存不足'})

        # 存入redis
        conn.hset(cart_key, sku_id, old_count)

        goods_count = conn.hlen(cart_key)

        return JsonResponse({'res' :5, 'errmsg': '添加成功','goods_count' : goods_count})

class UpdateCart(View):
    def post(self,request):

        if not request.user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'请先登录去'})

        count = request.POST.get('count')
        sku_id = request.POST.get('sku_id')

        if not all([count,sku_id]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 校验商品数量count
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '商品数量必须为有效数字'})

        # 链接redis数据库
        conn = get_redis_connection('default')

        cart_key = 'cart_%d' % request.user.id

        # 设置值
        conn.hset(cart_key,sku_id,count)

        return JsonResponse({'res':4,'errmsg':'更新成功'})

class DelCart(View):
    def post(self,request):
        if not request.user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录去'})

        sku_id = request.POST.get('sku_id')

        if sku_id is None:
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        conn = get_redis_connection('default')

        # 拼接key
        cart_key = 'cart_%d' % request.user.id

        conn.hdel(cart_key, sku_id)

        return JsonResponse({'res': 3, 'errmsg': '删除成功'})