# -*- coding: utf-8 -*-

import io

# 支持动态切换的Buffer，默认使用内存IO，如果数据超过指定大小则使用文件IO
class Buffer:
    def __init__(self, name, max_size=1024 * 1024 * 100):
        self.filename = "{0}_temp.dat".format(name)
        self.max_size = max_size
        self.buffer = io.BytesIO()
        self.file_buffer = None
        self.buffer_readable = False
        self.buffer_writeable = True

    def size(self):
        if self.file_buffer:
            pos = self.file_buffer.tell()
            self.file_buffer.seek(0, 2)  # 移动到文件末尾
            size = self.file_buffer.tell()
            self.file_buffer.seek(pos)  # 恢复到原来的位置
            return size
        else:
            pos = self.buffer.tell()
            self.buffer.seek(0, 2)  # 移动到内存末尾
            size = self.buffer.tell()
            self.buffer.seek(pos)  # 恢复到原来的位置
            return size

    def write(self, data):
        assert self.buffer_writeable, "Buffer不可写"
        if self.file_buffer:
            self.file_buffer.write(data)
        else:
            self.buffer.write(data)
            if self.buffer.tell() > self.max_size:
                # 切换到文件IO
                self.file_buffer = io.FileIO(self.filename, "wb")
                self.file_buffer.write(self.buffer.getvalue())
                self.buffer.close()
                self.buffer = None

    def flip(self):
        # Buffer写入完成后，必须调用flip()方法切换到可读状态
        assert self.buffer_writeable, "Buffer不可写"
        if self.file_buffer:
            self.file_buffer.close()
            self.file_buffer = io.FileIO(self.filename, "rb")
            self.buffer_writeable = False
            self.buffer_readable = True
        else:
            self.buffer_writeable = False
            self.buffer_readable = True
            self.buffer.seek(0)

    def read(self, size=-1):
        assert self.buffer_readable, "Buffer不可读"
        if self.file_buffer:
            data = self.file_buffer.read(size)
            return data
        else:
            return self.buffer.read(size)

    def readline(self):
        assert self.buffer_readable, "Buffer不可读"
        if self.file_buffer:
            data = self.file_buffer.readline()
            return data
        else:
            return self.buffer.readline()

    def get_value(self):
        assert self.buffer_readable, "Buffer不可读"
        if self.file_buffer:
            self.file_buffer.seek(0)
            data = self.file_buffer.read()
            return data
        else:
            self.buffer.seek(0)
            return self.buffer.getvalue()

