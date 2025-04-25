# -*- coding:utf-8 -*-

import os
import uuid

from .request import Request
from .buffer import Buffer

# Session类
class Session:
    # 默认接收数据大小
    DEFAULT_RECV_SIZE = 1024 * 1024
    DEFAULT_MEMORY_SIZE = 1024 * 1024 * 100

    def __init__(self, client_sock, request:Request):
        self.client_sock = client_sock
        self.request = request
        self.session_id = uuid.uuid4().hex
        self.close_connection = True
        self.is_closed = False
        self.read_fd = os.fdopen(client_sock.fileno(), 'rb', 0)
        self.raw_buffer = Buffer(self.session_id, self.DEFAULT_MEMORY_SIZE)

    def read(self, size):
        # 读取指定大小字节的数据
        try:
            return self.read_fd.read(size)
        except Exception as e:
            pass
        return None

    def read_line(self):
        # 读取一行数据
        try:
            line = self.read_fd.readline()
            return line.decode()
        except Exception as e:
            pass
        return None

    def send_error(self, code, msg):
        pass

    def send(self, raw):
        self.client_sock.send(raw)

    def finish(self):
        self.client_sock.flush()

    def close(self):
        self.client_sock.close()

    @property
    def version(self):
        return self.request.version
    @version.setter
    def version(self, value):
        self.request.version = value

    @property
    def method(self):
        return self.request.method
    @method.setter
    def method(self, value):
        self.request.method = value

    @property
    def path(self):
        return self.request.path
    @path.setter
    def path(self, value):
        self.request.path = value
