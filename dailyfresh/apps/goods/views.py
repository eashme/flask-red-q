from django.shortcuts import render
from django.views.generic import View
from apps.goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
# Create your views here.

class IndexView(View):
    def get(self,request):
        # 获取商品的分类信息
        types = GoodsType.objects.all()
        # 获取首页的轮播商品的信息
        goods_banners = IndexGoodsBanner.objects.all().order_by('index')
        # 获取首页的促销活动的信息
        goods_promotion = IndexPromotionBanner.objects.all().order_by('index')
        print(goods_promotion[0].image.url)
        # 获取首页分类商品的展示信息
        for type in types:
            # 标题显示的商品信息
            type_title = IndexTypeGoodsBanner.objects.filter(type=type,display_type=0)
            # 图片显示的商品信息
            type_image = IndexTypeGoodsBanner.objects.filter(type=type,display_type=1)
            #  将查询到的信息保存到type对象中
            type.type_title = type_title
            type.type_image = type_image

        # 组织要返回的数据
        context = {
            'types' : types,
            'goods_banners' : goods_banners,
            'goods_promotion' : goods_promotion,
        }
        return render(request, "index.html", context)

class DetailView(View):
    def get(self,request):

        return render(request,'detail.html')