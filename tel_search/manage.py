from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand


from apps import Init_App

get_app = Init_App(env='default')

# 使用Init_App的call方法获取app
app = get_app()

# 防止models模块不被加载,需要在使用前先导入一下,
# 由于models模块使用到了Init_App类要放在它第一次实例化之后引用
from apps import models

# 脚本管理器实例
manager = Manager(app)
Migrate(app, get_app.db)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    print(app.url_map)
    manager.run()