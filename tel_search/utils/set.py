# -*- coding:utf-8 -*-

class BaseSet(object):
    def add_fp(self, fp):
        pass

    def is_repeat(self,fp):
        pass


class NormalSet(BaseSet):
    def __init__(self):
        self._filter_set = set()

    def add_fp(self, fp):
        """添加元素"""
        self._filter_set.add(fp)

    def is_repeat(self, fp):
        """判断是否存在"""
        return True if fp in self._filter_set else False


class RedisSet(BaseSet):
    def __init__(self, name, redis_conn):
        """
        Reids集合
        :param name: redis数据库　键
        :param redis_conn: redis链接
        """
        self.name = name
        self.redis = redis_conn

    def add_fp(self, fp):
        """添加元素"""
        self.redis.sadd(self.name,fp)

    def is_repeat(self, fp):
        """判断是否存在"""
        return self.redis.sismember(self.name,fp)
