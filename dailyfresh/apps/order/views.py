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
from django.db import transaction
from utils.pay_helper import alipay
from django.conf import settings
import os


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
            sku.amount = round(int(count) * float(sku.price),2)

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
            'total_amount' : round(total_amount,2),
            'transffer_price' : round(transffer_price,2),
            'total_price' : round(total_price,2),
            'addrs' : addrs,
            'sku_ids' : ','.join(sku_ids)
        }

        return render(request,'place_order.html',context)


# 悲观锁(加mysql的互斥锁for update)
class OrderCommitView1(View):
    """悲观锁"""
    # 开启事务装饰器
    @transaction.atomic
    def post(self,request):
        """订单并发 ———— 悲观锁"""
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

        # 创建保存点
        sid = transaction.savepoint()

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
            # 尝试查询商品
            # 此处考虑订单并发问题,
            try:
                # sku = GoodsSKU.objects.get(id=sku_id)  # 不加锁查询
                sku = GoodsSKU.objects.select_for_update().get(id=sku_id)  # 加互斥锁查询
            except GoodsSKU.DoesNotExist:
                # 回滚到保存点
                transaction.rollback(sid)
                return JsonResponse({'res':2,'errmsg':'商品信息错误'})
            # 取出商品数量
            count = conn.hget(cart_key,sku_id)
            if count is None:
                # 回滚到保存点
                transaction.rollback(sid)
                return JsonResponse({'res':3,'errmsg':'商品不在购物车中'})

            count = int(count)

            if sku.stock < count:
                # 回滚到保存点
                transaction.rollback(sid)
                return JsonResponse({'res':4,'errmsg':'库存不足'})

            # 商品销量增加
            sku.sales += count
            # 商品库存减少
            sku.stock -= count
            # 保存到数据库
            sku.save()

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

        # 事务提交
        transaction.commit()



        return JsonResponse({'res':5,'errmsg':'订单创建成功'})

# 乐观锁(先查一遍库存,更新时将查询的库存作为限制条件,修改不成功就再去查库存,尝试3次)
class OrderCommitView(View):
    """乐观锁"""
    # 开启事务装饰器
    @transaction.atomic
    def post(self,request):
        """订单并发 ———— 乐观锁"""
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

        # 创建保存点
        sid = transaction.savepoint()

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
            # 尝试查询商品
            # 此处考虑订单并发问题,

            # redis中取出商品数量
            count = conn.hget(cart_key, sku_id)
            if count is None:
                # 回滚到保存点
                transaction.savepoint_rollback(sid)
                return JsonResponse({'res': 3, 'errmsg': '商品不在购物车中'})
            count = int(count)


            for i in range(3):
                # 若存在订单并发则尝试下单三次
                try:

                    sku = GoodsSKU.objects.get(id=sku_id)  # 不加锁查询
                    # sku = GoodsSKU.objects.select_for_update().get(id=sku_id)  # 加互斥锁查询
                except GoodsSKU.DoesNotExist:
                    # 回滚到保存点
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res':2,'errmsg':'商品信息错误'})


                origin_stock = sku.stock

                print(origin_stock, 'stock')
                print(sku.id, 'id')

                if origin_stock < count:

                    # 回滚到保存点
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res':4,'errmsg':'库存不足'})

                # # 商品销量增加
                # sku.sales += count
                # # 商品库存减少
                # sku.stock -= count
                # # 保存到数据库
                # sku.save()

                # 如果下单成功后的库存
                new_stock = sku.stock - count
                new_sales = sku.sales + count

                res = GoodsSKU.objects.filter(stock=origin_stock,id=sku_id).update(stock=new_stock,sales=new_sales)
                print(res)
                if res == 0:
                    if i == 2:
                        # 回滚
                        transaction.savepoint_rollback(sid)
                        return JsonResponse({'res':5,'errmsg':'下单失败'})
                    continue
                else:
                    break

            OrderGoods.objects.create(
                order = order_info,
                sku = sku,
                count = count,
                price = sku.price
            )

            # 删除购物车中记录
            conn.hdel(cart_key,sku_id)
            # 累加商品件数
            total_count += count
            # 累加商品总价
            total_amount += (sku.price) * count

        # 更新订单信息中的商品总件数
        order_info.total_count = total_count
        # 更新订单信息中的总价格
        order_info.total_price = total_amount + order_info.transit_price
        order_info.save()

        # 事务提交
        transaction.savepoint_commit(sid)



        return JsonResponse({'res':6,'errmsg':'订单创建成功'})

class AliPayOrder(View):
    def post(self,request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        order_id = request.POST.get('order_id')
        if order_id is None:
            return JsonResponse({'res':1,'errmsg':'数据不完整'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                  # pay_method=3,  # 支付方式为支付宝支付
                                  user=user,
                                  order_status=1    #支付状态为待支付
                                  )
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单不存在'})



        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string

        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 商户订单号
            total_amount=str(order.total_price),  # 订单总金额
            subject=settings.ALIPAY_TITLE,  # 订单标题
            return_url=settings.ALIPAY_RETURN_URL,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 生成支付地址
        pay_url = settings.ALIPAY_URL + order_string

        return JsonResponse({'res':3, 'errmsg':'OK','pay_url': pay_url})


    def get(self,request):
        '''查询支付结果页面'''
        # total_amount = 180.00　　　　# 参数总价
        # trade_no = 2018031921001004270200397232  # 交易编号
        # out_trade_no = 201803181715246　　# 订单编号

        # 支付宝交易编号
        trade_no = request.GET.get('trade_no')
        # 订单编号
        out_trade_no = request.GET.get('out_trade_no')

        res = alipay.api_alipay_trade_query(trade_no=trade_no)
        # res 结构
        # {'invoice_amount': '0.00', 'code': '10000', 'buyer_user_type': 'PRIVATE', 'total_amount': '100.00',
        #  'receipt_amount': '0.00', 'buyer_user_id': '2088102175534275', 'buyer_logon_id': 'rcq***@sandbox.com',
        #  'send_pay_date': '2018-03-19 16:59:55', 'out_trade_no': '201803191657596',
        #  'trade_no': '2018031921001004270200397406', 'buyer_pay_amount': '0.00', 'point_amount': '0.00',
        #  'msg': 'Success', 'trade_status': 'TRADE_SUCCESS'}

        code = res.get("code")
        trade_status = res.get('trade_status')
        trade_msg = res.get('msg')

        if code == '10000' and trade_status =="TRADE_SUCCESS" and trade_msg == 'Success':
            # 付款成功
            order = OrderInfo.objects.get(order_id=out_trade_no)
            # 记录支付编号
            order.trade_no = trade_no
            # 更改支付状态
            order.order_status = 2
            order.save()
            return HttpResponse('支付成功')
        else:
            return HttpResponse('支付失败')
