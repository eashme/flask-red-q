from django.shortcuts import render,redirect
from django.views.generic import View
from apps.goods.models import GoodsSKU
from apps.user.models import Address
from apps.order.models import OrderInfo,OrderGoods
from utils.mixin import LoginRequireMixin
from django_redis import get_redis_connection
from django.http import JsonResponse,HttpResponse
from django.core.urlresolvers import reverse
from datetime import datetime

# Create your views here.

class OrderPlace(LoginRequireMixin, View):
    def post(self, request):
        """订单处理页面"""
        # 通过提交的数据
        sku_ids = request.POST.getlist('skus_id')
        # 拼接key
        cart_key = 'cart_%d' % request.user.id
        # 获取redis链接
        conn = get_redis_connection('default')

        # 获取地址
        addrs = Address.objects.filter(user=request.user)

        # 商品件数
        total_count = 0
        # 总金额
        total_amount = 0

        skus = []
        # 遍历id列表拿出所有的商品id
        for sku_id in sku_ids:
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                # 没拿到商品重定向到首页去
                return redirect(reverse('goods:index'))

            count = conn.hget(cart_key, sku_id)

            if count is None:
                # 没拿到对应的数量重定向到首页去
                return redirect(reverse('goods:index'))

            sku.count = int(count)
            sku.amount = int(count) * float(sku.price)

            skus.append(sku)

            total_count += sku.count
            total_amount += sku.amount
        # 运费
        transffer_price = 10
        # 实付款
        total_price = total_amount + transffer_price

        # 组织模板变量
        context = {
            'skus' : skus,
            'total_count' : total_count,
            'total_amount' : total_amount,
            'transffer_price' : transffer_price,
            'total_price' : total_price,
            'addrs' : addrs,
            'sku_ids' : ','.join(sku_ids)
        }

        return render(request,'place_order.html',context)

class OrderCommitView(View):
    def post(self,request):
        # 拿到id
        sku_ids_str = request.POST.get('sku_ids')
        sku_ids = sku_ids_str.split(',')

        if len(sku_ids) == 0 :
            return JsonResponse({'res':0,'errmsg':'数据不完整'})

        # 当前时间字符串
        now_str = datetime.now().strftime('%Y%m%d%H%M%S')

        # 订单编号
        order_id = now_str + str(request.user.id)
        # 地址
        pay_method = request.POST.get('pay_method')
        # 支付方式
        address_id = request.POST.get('address_id')
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':1,'errmsg':'地址错误'})

        # 商品数量
        total_count = 0
        # 商品总价
        total_amount = 0
        # 订单运费
        transit_price = 10
        order_info = OrderInfo.objects.create(
            order_id = order_id,
            user = request.user,
            addr = address,
            pay_method = pay_method,
            total_count = total_count,
            total_price = total_amount,
            transit_price = transit_price
        )
        # 获取redis连接
        conn = get_redis_connection('default')
        # 拼接key
        cart_key = 'cart_%d' % request.user.id

        for sku_id in sku_ids:

            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                return JsonResponse({'res':2,'errmsg':'商品信息错误'})
            # 取出商品数量
            count = conn.hget(cart_key,sku_id)
            if count is None:
                return JsonResponse({'res':3,'errmsg':'商品不在购物车中'})

            count = int(count)

            OrderGoods.objects.create(
                order = order_info,
                sku = sku,
                count = count,
                price = sku.price
            )
            # 累加商品件数
            total_count += count
            # 累加商品总价
            total_amount += (sku.price) * count

        # 更新订单信息中的商品总件数
        order_info.total_count = total_count
        # 更新订单信息中的总价格
        order_info.total_price = total_amount + order_info.transit_price
        order_info.save()

        return JsonResponse({'res':4,'errmsg':'订单创建成功'})

