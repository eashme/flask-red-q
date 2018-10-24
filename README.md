使用redis做的一个任务队列,使用flask提供api进行任务发布

轮询模式进行任务和结果查询,后面有时间再仿造 epoll模型使用redis的键空间通知功能做一个

程序入口是 manage.py文件,直接 python manage.py runserver -h IP地址 -p端口号就可以开始运行

程序运行之前要先修改配置文件中的  redis连接参数

代码中的注释我习惯写的非常详细。
