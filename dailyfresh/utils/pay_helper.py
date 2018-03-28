from alipay import AliPay
from django.conf import settings


class MyAlipay(AliPay):
    """单例模式,只使用一个实例操作支付"""
    __alipay_Obj = None  # 保存第一次创建的对象
    __has_init = False  # 记录是否已经初始化

    def __new__(cls, *args, **kwargs):
        # 如果已经创建过对象了就不创建了返回以前保存的
        if cls.__alipay_Obj is None:
            cls.__alipay_Obj = super().__new__(cls,*args)

        return cls.__alipay_Obj

    def __init__(self, *args, **kwargs):
        # 如果已经初始化过了,就不再初始化了
        if not self.__has_init:
            MyAlipay.__has_init = True
            super().__init__(*args, **kwargs)


# 创建支付宝SDK对象
alipay = MyAlipay(**(settings.ALIPAY_SETTING))
