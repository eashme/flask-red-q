# -*- coding:utf-8 -*-
from functools import wraps
from flask import session, jsonify, g
from werkzeug.routing import BaseConverter
from utils.response_code import RET

class RegxConverter(BaseConverter):
    def __init__(self, url_map, *args):
        """自定义路由规则为参数"""

        # 保存自定义的正则规则
        self.regex = args[0]
        # 执行父类的init方法
        super(RegxConverter, self).__init__(url_map)


def login_required(view_func):

    # 使用wraps装饰之后可以保留原来函数的描述信息和函数名
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if user_id:
            g.user_id = user_id
            return view_func(*args, **kwargs)
        else:
            return jsonify({'errno': RET.SESSIONERR, 'errmsg': '用户未登录'})

    return wrapper
