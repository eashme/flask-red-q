# -*- coding:utf-8 -*-
import time, pickle

import redis

try:
    from queue import Empty, Full
except ImportError:
    from Queue import Empty, Full


class Queue(object):
    Empty = Empty
    Full = Full
    max_timeout = 0.3

    def __init__(self, name, redis, maxsize=0, lazy_limit=True, ):
        """
        Constructor for RedisQueue
        name: 队列在数据库中的名称
        redis: redis链接对象
        maxsize:    redis数据库队列的最大长度
        lazy_limit: 动态限制redis队列长度
        """
        self.name = name
        self.redis = redis
        self.maxsize = maxsize
        self.lazy_limit = lazy_limit
        self.last_qsize = 0

    def qsize(self):
        """获取队列长度"""
        self.last_qsize = self.redis.llen(self.name)
        return self.last_qsize

    def empty(self):
        """返回队列是否为空"""
        if self.qsize() == 0:
            return True
        else:
            return False

    def full(self):
        """判断队列是否超过队列规定长度"""
        if self.maxsize and self.qsize() >= self.maxsize:
            return True
        else:
            return False

    def put_nowait(self, obj):
        """非阻塞的向队列中加入元素"""
        if self.lazy_limit and self.last_qsize < self.maxsize:
            # 如果队列没有超出长度限制,并且动态限制开启
            pass
        elif self.full():
            # 队列超出了长度限制,抛出异常
            raise self.Full
        # 使用pickle将python对象转为二进制字符串,存入redis列表中
        self.last_qsize = self.redis.rpush(self.name, pickle.dumps(obj))
        return True

    def put(self, obj, block=True, timeout=None):
        """
        obj:        要存入的python对象
        block:      是否阻塞存入
        timeout:    每次休眠时长
        """
        if not block:
            # 不阻塞的存入
            return self.put_nowait(obj)

        # 开始计时
        start_time = time.time()
        while True:
            try:
                return self.put_nowait(obj)
            except self.Full:
                if timeout:
                    # 设置了休眠时间
                    lasted = time.time() - start_time  # 距离开始计时已经过了的时间
                    if timeout > lasted:  # 每次休眠时长大于当前过的秒数
                        time.sleep(min(self.max_timeout, timeout - lasted))
                    else:
                        # 如果超出了设置的阻塞时长　抛出异常
                        raise TimeoutError
                else:
                    # 如果没有设置休眠时长使用默认的0.3秒休眠
                    time.sleep(self.max_timeout)

    def get_nowait(self):
        """不阻塞的从redis中取数据"""
        # 直接取数据
        ret = self.redis.lpop(self.name)
        if ret is None:
            # 如果没取到就抛异常
            raise self.Empty
        # 返回取出来的结果,用pickle将其读为python对象
        return pickle.loads(ret)

    def get(self, block=True, timeout=None):
        """
        :param block: 是否阻塞
        :param timeout: 阻塞时长
        :return:
        """
        if not block:
            # 不阻塞的读取
            return self.get_nowait()
        # 开始计时
        start_time = time.time()
        while True:
            try:
                # 尝试直接读取
                return self.get_nowait()
            except self.Empty:
                # 阻塞
                if timeout:
                    lasted = time.time() - start_time
                    # 超出阻塞时间了抛出异常
                    if timeout > lasted:
                        # 设置了阻塞时间,　以默认的休眠时间和设置的休眠时间与当前过得时间小的那个为一次休眠时长
                        time.sleep(min(self.max_timeout, timeout - lasted))
                    else:
                        # 　阻塞时间超时了抛出异常
                        raise TimeoutError
                else:
                    # 未设置阻塞时间一值阻塞
                    time.sleep(self.max_timeout)


