from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import Fdfs_client

class FDFStorage(Storage):
    def __init__(self, nginx_url=None, fdfs_client_conf=None):
        # 如果传入了Nginx服务器的url就用传入的,否则使用配置文件中的
        if nginx_url is None:
            self.nginx_url = settings.NGINX_URL
        else:
            self.nginx_url = nginx_url
        # 如果传入了fdfs的连接配置文件路径就用传入的,否则用配置文件中的
        if fdfs_client_conf is None:
            self.fdfs_client_conf = settings.FDFS_CLIENT_CONF
        else:
            self.fdfs_client_conf = fdfs_client_conf

    def _save(self, name, content):
        # 创建fdfs链接
        client = Fdfs_client(self.fdfs_client_conf)
        # 上传文件到fdfs服务器
        res = client.upload_by_buffer(content.read())
        # return dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id, # 文件在fdfs服务器保存的路径
        #     'Status': 'Upload successed.',    # 文件上传状态，是否成功
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # } if success else None

        # 如果上传失败抛出异常
        if res.get('Status') != 'Upload successed.' or res is None:
            raise Exception('文件上传到FDFS系统失败')

        # 数据库中的image字段会记录_save的返回值
        return res.get('Remote file_id')

    def exists(self, name):
        # 是FDFS系统对上传的文件进行文件管理所以不会出现重名问题
        # 直接return False告诉django不重名就行
        return False

    def url(self, name):
        # name返回的就是文件在FDFS系统中存储的路径,拼接上Nginx服务器的url就可以对该文件进行访问
        return self.nginx_url + name