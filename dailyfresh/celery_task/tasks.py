from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader


# 这两行代码在启动worker进行的一端打开
# 设置django配置依赖的环境变量
import os
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# 初始化模型类需要的环境
# import django
# django.setup()

from apps.goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner

app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/12')

app.conf.broker_url = 'redis://127.0.0.1:6379/0'
# 发送邮件的celery任务
@app.task
def send_register_active_email(to_email,username,token):
    """发送激活邮件"""
    # 组织邮件内容
    subject = '天天生鲜欢迎激活邮件'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = """
                        <h1>%s, 欢迎您成为天天生鲜注册会员</h1>
                        请点击以下链接激活您的账户<br/>
                        <a href="http://127.0.0.1:8000/user/active?token=%s">http://127.0.0.1:8000/user/active?token=%s</a>
                    """ % (username, token, token)

    # 发送激活邮件
    # send_mail(subject=邮件标题, message=邮件正文,from_email=发件人, recipient_list=收件人列表)
    send_mail(subject, message, sender, receiver, html_message=html_message)

@app.task
def genarate_static_index_html():
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

    # 1.加载模板文件,获取模板对象,返回Template
    temp = loader.get_template('index.html')
    # 数据渲染模板
    res_html = temp.render(context)
    static_index_path = os.path.join(settings.BASE_DIR,'static/gen_static_index.html')
    # 将渲染好的静态页面写入文件中
    with open(static_index_path,'w') as f:
        f.write(res_html)




