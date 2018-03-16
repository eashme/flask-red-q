from django.contrib import admin
from apps.goods.models import GoodsSKU,GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
from django.core.cache import cache
from celery_task.tasks import genarate_static_index_html
# Register your models here.

class BaseAdminMode(admin.ModelAdmin):

    def save_data_to_cache(self):
        # 获取商品的分类信息
        types = GoodsType.objects.all()
        # 获取首页的轮播商品的信息
        goods_banners = IndexGoodsBanner.objects.all().order_by('index')
        # 获取首页的促销活动的信息
        goods_promotion = IndexPromotionBanner.objects.all().order_by('index')

        # 获取首页分类商品的展示信息
        for type in types:
            # 标题显示的商品信息
            type_title = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0)
            # 图片显示的商品信息
            type_image = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1)
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

        # 发出celery任务,重新生成静态文件
        genarate_static_index_html.delay()

    def save_model(self, request, obj, form, change):
        # 调用原来的保存方法执行保存操作
        super().save_model(request, obj, form, change)

        # 更新缓存中的数据
        self.update_data_to_cache()


    def delete_model(self, request, obj):
        # 调用原来delete_model执行删除操作
        super().delete_model(request, obj)

        # 更新缓存中的数据
        self.update_data_to_cache()


class GoodsTypeAdmin(BaseAdminMode):
    pass

class IndexGoodsBannerAdmin(BaseAdminMode):
    pass

class IndexPromotionBannerAdmin(BaseAdminMode):
    pass

class IndexTypeGoodsBannerAdmin(BaseAdminMode):
    pass


# 注册到管理界面
admin.site.register(GoodsType,GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner,IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner,IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner,IndexTypeGoodsBannerAdmin)