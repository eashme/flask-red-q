from django.shortcuts import render,redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from apps.goods.models import GoodsSKU,GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
from apps.order.models import OrderGoods
from django_redis import get_redis_connection
from django.core.cache import cache
from celery_task.tasks import genarate_static_index_html
from django.core.paginator import Paginator

# Create your views here.

class IndexView(View):
    def get(self,request):
        """用cache保存首页拿到的数据库数据"""
        # 发出生成静态文件的任务
        genarate_static_index_html.delay()

        # 取cache值get(key)
        context = cache.get('index_page_data')
        if context is None:
            # 获取商品的分类信息
            types = GoodsType.objects.all()
            # 获取首页的轮播商品的信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')
            # 获取首页的促销活动的信息
            goods_promotion = IndexPromotionBanner.objects.all().order_by('index')

            print(goods_banners[0].image.url)
            # 获取首页分类商品的展示信息
            for type in types:
                # 标题显示的商品信息
                type_title = IndexTypeGoodsBanner.objects.filter(type=type,display_type=0)
                # 图片显示的商品信息
                type_image = IndexTypeGoodsBanner.objects.filter(type=type,display_type=1)
                #  将查询到的信息保存到type对象中
                type.type_title = type_title
                type.type_image = type_image

            # 购物车商品数量
            cart_count = 0
            # 查询到的数据
            context = {
                'types': types,
                'goods_banners': goods_banners,
                'goods_promotion': goods_promotion,
                'cart_count': cart_count,
            }

            # 将查询到的数据使用cache进行存储
            # 设置cache值set(key, value, timeout)
            cache.set('index_page_data', context, 3600)


        if request.user.is_authenticated():
            # 拿到用户的购物车商品数量
            cart_key = 'cart_%d' % request.user.id
            conn = get_redis_connection('default')
            cart_count = conn.hlen(cart_key)
            context.update(cart_count=cart_count)


        return render(request, "index.html", context)

class DetailView(View):
    def get(self,request,sku_id):
        sku_id = int(sku_id)
        try:
            # 通过商品id拿到商品
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在，跳转到首页
            return redirect(reverse('goods:index'))

        # 获取商品分类信息
        types = GoodsType.objects.all()
        # 获取评论信息
        order_skus = OrderGoods.objects.filter(sku=sku).exclude(comment='').order_by('-update_time')
        # 获取和商品同一个SPU的其他规格的商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku_id)

        # 获取和商品同一种类的两个新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 如果用户登录，获取用户购物车中商品的条目数
        cart_count = 0
        if request.user.is_authenticated():
            # 拿到用户的购物车商品数量
            cart_key = 'cart_%d' % request.user.id
            conn = get_redis_connection('default')
            cart_count = conn.hlen(cart_key)

            # 将用户浏览记录保存到redis中
            # 拼接出key
            history_key = 'history_%d' % request.user.id
            # 先尝试从redis中删除该商品id
            # lrem(key,count,value)
            conn.lrem(history_key, 0, sku_id)
            # 将记录保存到redis中
            conn.lpush(history_key,sku_id)
            # 只保存五条浏览记录
            # ltrim(key, start, stop)
            conn.ltrim(history_key, 0, 4)

        # 组织模板变量
        context = {
            'sku' : sku,
            'types' : types,
            'order_skus' : order_skus,
            'same_spu_skus' : same_spu_skus,
            'new_skus' : new_skus,
            'cart_count' : cart_count,
        }


        return render(request,'detail.html',context)

class ListView(View):
    def get(self,request,type_id,page):

        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            #商品种类不存在,跳转到首页
            return redirect(reverse('goods:index'))

        # 获取所有商品种类
        types = GoodsType.objects.all()

        # 获取排序方式
        # sort=price: 按照商品的价格(price)从低到高排序
        # sort=hot: 按照商品的人气(sales)从高到低排序
        # sort=default: 按照默认排序方式(id)从高到低排序
        sort = request.GET.get('sort')

        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'sales':
            skus = GoodsSKU.objects.filter(type=type).order_by('sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        # 获取该种类的两个新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 分页
        paginator = Paginator(skus,1)

        try:
            page = int(page)
        except TypeError:
            page = 1

        # 无效的页码设置为１
        if (page > paginator.num_pages) or (page < 0):
            page = 1

        skus_page = paginator.page(page)

        # 如果用户登录，获取用户购物车中商品的条目数
        cart_count = 0
        if request.user.is_authenticated():
            # 拿到用户的购物车商品数量
            cart_key = 'cart_%d' % request.user.id
            conn = get_redis_connection('default')
            cart_count = conn.hlen(cart_key)

        # 页码处理
        # 如果分页之后页码超过5页，最多在页面上只显示5个页码：当前页前2页，当前页，当前页后2页
        # 1) 分页页码小于5页，显示全部页码
        if paginator.num_pages < 5:
            pages = range(1, paginator.num_pages + 1)
        # 2）当前页属于1-3页，显示1-5页
        elif skus_page.number < 4 :
            pages = range(1, 6)
        # 3) 当前页属于后3页，显示后5页
        elif skus_page.number > paginator.num_pages - 3 :
            pages = range(paginator.num_pages - 4, paginator.num_pages + 1)
        # 4) 其他请求，显示当前页前2页，当前页，当前页后2页
        else:
            pages = range(skus_page.number -2, skus_page.number + 3)


        context = {
            'type' : type,
            'types' : types,
            'skus_page' : skus_page,
            'sort' : sort,
            'cart_count' : cart_count,
            'new_skus' : new_skus,
            'pages' : pages,
        }
        return render(request, 'list.html', context)