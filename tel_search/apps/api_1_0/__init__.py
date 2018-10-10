from flask import Blueprint

api = Blueprint('api_1_0', __name__, url_prefix='/api/1.0')

html_blueprint = Blueprint('html_api',__name__)


# 视图函数写完要到此处进行导入一次,否则无法加入路由中
from . import gen_task