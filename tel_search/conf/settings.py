import redis, logging


class Config(object):
    """配置项"""
    # debug模式
    DEBUG = True

    # 使用base64.b64encode(os.urandom(48)) 生成的秘钥
    SECRET_KEY = 'qxQtcui9oC/C6wbN5IxUriIXP1A59/m9FCAGirf2GmFht8UvQ2isbtDADkHTG128'
    # 数据库链接配置项   mysql://username:password@localhost/mydatabase
    SQLALCHEMY_DATABASE_URI = 'mysql://root:mysql@127.0.0.1:3306/iHome'
    # 是否开启数据库增删改查追踪(很耗费性能)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # redis数据库主机
    # REDIS_HOST = '127.0.0.1'
    REDIS_HOST = '192.168.28.134'
    # redis数据库端口
    REDIS_PORT = '6379'
    # redis 数据库
    REDIS_SELECT = 5
    # redis 数据库密码
    REDIS_PWD = None
    # redis　数据库字符集
    REDIS_CHARSET = None

    # session相关配置
    SESSION_TYPE = 'redis'
    # 存储session的数据库的相关配置
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_SELECT)
    # session的存储格式 默认的 session:
    # SESSION_KEY_PREFIX 一般用默认的不做设置
    # 是否使用签名
    SESSION_USE_SIGNER = False
    # 是否开启session设置过期时间
    # SESSION_PERMANENT = True
    # session存储时长
    PERMANENT_SESSION_LIFETIME = 3600 * 24
    # 日志等级
    LOGGER_LEVAL = logging.DEBUG
    # 任务响应超时时间(秒)
    TASK_TIMEOUT = 1 * 60

class DevelopmentConfig(Config):
    pass
    # 日志等级
    LOGGER_LEVAL = logging.DEBUG


class ProductionConfig(Config):
    # debug模式
    DEBUG = False
    # 日志等级
    LOGGER_LEVAL = logging.WARNING


class UnitetestConfig(Config):
    pass


configs = {
    'default': Config,
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'unitetest': UnitetestConfig
}
