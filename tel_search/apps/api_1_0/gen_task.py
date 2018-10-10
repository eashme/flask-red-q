from flask import current_app, request, jsonify
import time
from werkzeug.security import generate_password_hash
from utils.queue import Queue
from apps import redis_conn
from utils.response_code import RET, error_map
from . import api


@api.route('/search', methods=['POST'])
def gen_task():
    # 获取通过Json传递进来的数据
    request_dict = request.json

    """
    {
        d:[134xxxxxxxx,139xxxxxxxx,184xxxxxxxx]
    }
    """
    # 获取要查询的手机号
    tels = request_dict.get('d')

    if not tels:
        return jsonify({'errno': RET.PARAMERR, 'errmsg': error_map[RET.PARAMERR]})

    task_id = generate_password_hash("task_%d" % (int(time.time() * 1000) % 10000000000))
    task = {
        'task_id': task_id,
        'tels': tels
    }

    current_app.task_queue.put_nowait(task)

    return jsonify({'code': RET.OK, 'message': '任务发布成功', 'task_id': task_id})


@api.route('/res', methods=['POST'])
def get_queue():
    task_id = request.json.get('task_id')
    res_queue = Queue(task_id, redis_conn)
    counter = 0
    while True:
        try:
            res = res_queue.get_nowait()
        except res_queue.Empty:
            if counter >= current_app.config.get('TASK_TIMEOUT'):
                return jsonify({'code': RET.SERVERERR, 'message': '响应超时'})
            counter += 1
            time.sleep(1)
        else:
            if res == 0:
                return jsonify({'code': RET.NODATA, 'message': '没有数据了,别再请求了'})
            else:
                return jsonify({'code': RET.OK, 'res': res, 'message': '获取成功,还有结果请继续请求'})
