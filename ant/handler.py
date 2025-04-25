# -*- coding:utf-8 -*-

import io,os,time

from .response import Response
from .request import Request

class RequestHandler:
    def __init__(self, request:Request):
        self.request = request
        self.response = Response(200, {}, '')

    def set_status(self, code, msg=""):
        self.response.status_code = code
        if msg:
            self.response.body = msg

    def set_header(self, name, value):
        self.response.set_header(name, value)

    def write(self, body, immediately=False):
        if immediately:
            self.response.body += body
        else:
            self.response.body = body

    def write_error(self, code, msg=None, body=None):
        self.set_status(code, msg)
        if body:
            self.response.body = body
        else:
            self.response.body = f"Error {code}: {msg}"


class StaticFileHandler(RequestHandler):
    """ 下载静态文件 """
    def head(self):
        """
        head 请求
        :return:
        """
        return self.get(include_body=False)

    def do_cache_request(self, file_path, size, include_body, use_range=None):
        """
        执行缓存请求
        :param file_path:
        :param size:
        :param include_body:
        :param use_range:
        :return:
        """
        if Application.static_cache:
            if_modify_date = self.request.get_header("If-Modified-Since")
            cache_control = self.request.get_header("Cache-control")
            if not cache_control or cache_control.find("no-cache") < 0:
                file_modify_date = self.file_modify_date(file_path)
                if if_modify_date and if_modify_date == file_modify_date and not use_range:
                    self.set_status(304)
                    return
                self.set_header("Cache-control", "no-cache")
                if not use_range:
                    self.set_header("Last-Modified", file_modify_date)
        if not Application.static_cache or not use_range:
            if not Application.chunk_support:
                self.set_header("Content-Length", size)
            if include_body:
                self.do_content_response(file_path)
        else:
            start, end = use_range
            # Range: -1024表示从资源末尾往前读取1024个字节的内容
            if start is None:
                start = size - end
            # Range: 0- 表示从资源开始到末尾，为了防止资源过大，这里并不一定需要一次性将全部读取返回
            if end is None:
                end = size - 1
            read_size = end - start + 1
            if read_size > Application.max_buff_size:
                read_size = Application.max_buff_size
                end = read_size + start - 1
            self.set_header("Content-Range", "bytes %s-%s/%s" % (start, end, size))
            self.set_header("Content-Length", read_size)
            self.set_status(206)
            if include_body:
                self.do_content_response(file_path, [start, read_size])

    def do_content_response(self, file_path, use_range=None):
        """
        读取文件内容
        :param file_path:
        :param use_range:
        :return:
        """
        with open(file_path, "rb") as fp:
            if not use_range:
                for line in fp:
                    self.write(line, immediately=True)
            else:
                fp.seek(use_range[0], io.SEEK_SET)
                chunk = fp.read(use_range[1])
                self.write(chunk, immediately=True)

    def get(self, include_body=True):
        """
        静态文件get请求
        :param include_body:
        :return:
        """
        file_path = self.get_file_path()
        if not file_path:
            return self.write_error(404, None, "%s is not exist" % file_path)
        # 如果不是允许下载的格式，则返回403
        minetype = self.getFileMimeType(file_path)
        if not minetype:
            return self.write_error(403)
        # 获取文件的总大小
        size = os.path.getsize(file_path)
        # 设置响应头，表示服务器支持Range格式请求
        if Application.static_cache:
            self.set_header("Accept-Ranges", "bytes")
        self.set_header("Content-Type", minetype)
        # 检查客户端的请求中是否采样Range格式请求
        range_header = self.request.get_header("Range")
        if not range_header:
            self.do_cache_request(file_path, size, include_body)
        else:
            start, end = self.parse_range(range_header)
            # 需要读取的起始位置不能为空，或者超出了文件的大小
            if (start is None and end is None) or \
                    (start is not None and start >= size) or \
                    (end is not None and end >= size):
                self.set_header("Content-Range", "bytes */%s" % (size,))
                self.write_error(416)
                return
            self.do_cache_request(file_path, size, include_body, use_range=[start, end])

    def get_file_path(self):
        """
        获取文件的路径
        """
        # 对url进行解码，有可能有带空格的文件之类的
        path = unquote(self.request.path)
        route = path if not path.startswith("/") else path[1:]
        file_path = os.path.join(Application.static_path, route)
        if not os.path.isfile(file_path) or not os.path.exists(file_path):
            return None
        return file_path

    @staticmethod
    def file_modify_date(file_path):
        """
        获取文件的最后修改时间
        :param file_path:
        :return:
        """
        file_mt = time.localtime(os.stat(file_path).st_mtime)
        return to_rfc822_date(file_mt)

    @staticmethod
    def parse_range(range_header):
        """
        解析请求头中的Range
        :param range_header:
        :return: 开始和结束位置，异常则返回空
        """
        unit, _, value = range_header.partition("=")
        unit, value = unit.strip(), value.strip()
        if unit != "bytes":
            return None
        start_b, _, end_b = value.partition("-")
        start = _int_or_none(start_b)
        end = _int_or_none(end_b)

        if end is not None:
            if start is None:
                if end != 0:
                    start = -end
                    end = None
            else:
                end += 1
        return start, end

    @staticmethod
    def getFileMimeType(filename):
        """ 根据文件扩展名获取文件类型 """
        dot_index = filename.rfind(".")
        if dot_index < 0:
            return "application/octet-stream"
        return Application.static_mime_type(filename[dot_index:])

