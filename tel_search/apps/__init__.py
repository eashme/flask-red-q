from flask_sqlalchemy import SQLAlchemy
import redis, logging
from flask_session import Session
from flask import Flask
from utils.queue import Queue

from utils.common import RegxConverter
from logging.handlers import RotatingFileHandler
from flask_wtf.csrf import CSRFProtect
from conf.settings import configs

db = SQLAlchemy()
redis_conn = None


class Init_App(object):
    """初始化app类"""

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if not hasattr(cls, '_init_app'):
            # 执行父类new方法创建init_app对象
            cls._init_app = super(Init_App, cls).__new__(cls, *args)

            # 实例flask应用
            cls._init_app.app = Flask(__name__)

        return cls._init_app

    def __init__(self, **kwargs):

        if not hasattr(Init_App, '_has_init'):

            if 'env' in kwargs.keys():
                env = kwargs['env']
            else:
                raise Exception('缺少环境配置参数env')

            # 加载配置项
            self.app.config.from_object(configs[env])

            # 开启csrf防护验证
            # CSRFProtect(self.app)

            # 设置日志
            self.set_log(self.app.config.get('LOGGER_LEVAL'))

            # 数据库链接实例
            self.db = db.init_app(self.app)

            # redis 数据库实例
            self.redis_conn = redis.StrictRedis(host=self.app.config.get('REDIS_HOST'),
                                                port=self.app.config.get('REDIS_PORT'),
                                                db=self.app.config.get('REDIS_SELECT'),
                                                password=self.app.config.get('REDIS_PWD'),
                                                charset=self.app.config.get('REDIS_CHARSET'))

            global redis_conn
            redis_conn = self.redis_conn

            self.app.task_queue = Queue('task',redis_conn)

            Session(self.app)

            # 将自定义的路由转换器加入列表
            self.app.url_map.converters['re'] = RegxConverter

            # 将蓝图中的路由注册到app中
            from apps.api_1_0 import api, html_blueprint

            self.app.register_blueprint(api)

            self.app.register_blueprint(html_blueprint)

            # 初始化完成,修改类属性has_init为True
            Init_App._has_init = True

    def set_log(self, leval):
        # 设置日志的记录等级
        logging.basicConfig(level=leval)  # 调试debug级
        # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
        file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
        # 创建日志记录的格式                 日志等级    输入日志信息的文件名 行数    日志信息
        formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
        # 为刚创建的日志记录器设置日志记录格式
        file_log_handler.setFormatter(formatter)
        # 为全局的日志工具对象（flask app使用的）添加日志记录器
        logging.getLogger().addHandler(file_log_handler)

    def __call__(self):
        """返回app实例"""
        return self.app


