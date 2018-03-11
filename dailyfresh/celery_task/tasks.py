from celery import Celery
from django.conf import settings
from django.core.mail import send_mail

# 这两行代码在启动worker进行的一端打开
# 设置django配置依赖的环境变量
# import os
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")


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

