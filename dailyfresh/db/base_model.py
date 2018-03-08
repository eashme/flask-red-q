from django.db import models

class BaseModel(models.Model):
    """抽象模型基类"""
    create_time = models.DateField(auto_now_add=True,verbose_name='创建时间')
    update_time = models.DateField(auto_now=True,verbose_name='更新时间')
    is_delete = models.BooleanField(default=False,verbose_name='删除标记')

    class Meta:
        """指定这是一个抽象模型基类"""
        abstract = True