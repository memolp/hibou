# -*- coding:utf-8 -*-

import asyncio
import cgi
import io
import os
import selectors
import socket
import ssl
import time
import logging
import urllib.parse
import uuid


RESPONSE_CODE_DEFINED = {
    100: 'Continue',
    101: 'Switching Protocols',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
}


MINE_TYPE_DEFINED = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.html': 'text/html',
    '.jpg': 'image/jpg',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.woff': 'text/font',
    '.woff2': 'text/font',
    '.ttf': 'text/font',
    ".xls": "application/xls",
    ".xlsx": "application/xlsx",
    ".doc": "application/doc",
    ".docx": "application/docx",
    ".pdf": "application/pdf",
    ".avi": "application/x-mplayer2",
    ".mp4": "video/mp4",
    ".moc": "application/octet-stream",
    ".json": "text/json",
    ".txt": "text/json",
    ".ico": "image/ico",
    ".mtn": "application/octet-stream",
    ".mp3": "application/octet-stream",
    ".mkv": "application/octet-stream",
    ".zip": "application/octet-stream",
    ".7z": "application/octet-stream",
    ".rar": "application/octet-stream",
    ".ipa": "application/vnd.iphone",
    ".apk": "application/vnd.android.package-archive",
}

class Utils:

    @staticmethod
    def int_or_none(value):
        # 返回一个整数，如果值为None或无法转换为整数，则返回None
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def to_rfc822(time_local, zone=None):
        # 将本地时间转换为RFC 822格式的字符串
        if zone is None:
            zone = "GMT"
        return time.strftime('%a, %d %b %Y %H:%M:%S {0}'.format(zone), time_local)

    @staticmethod
    def exec_code(code, glob, loc=None):
        # 执行给定的代码字符串
        if isinstance(code, str):
            code = compile(code, '<string>', 'exec', dont_inherit=True)
        exec(code, glob, loc)

    @staticmethod
    def to_utf8(data):
        # 将数据转换为UTF-8编码
        try:
            if isinstance(data, str):
                return data
            elif isinstance(data, bytes):
                return data.decode("utf-8")
            else:
                return str(data)
        except Exception as e:
            print(e)
        return data

    @staticmethod
    def html_escape(data):
        # 将数据进行HTML转义
        if isinstance(data, str):
            return data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#039;")
        return data


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


# 保存上传的文件类
class UploadFile:
    def __init__(self, filename, filetype, filedata):
        self.filename = filename
        self.filetype = filetype
        self.filedata = filedata

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self.filedata)
        return path


class HttpConfig:
    def __init__(self):
        self.logger = None      # type: logging.Logger or None
        self.logger_level = logging.INFO   # 日志等级
        self.namespace = {}
        self.static_path = None
        self.upload_path = None
        self.script_path = None
        self.template_path = None
        self.support_static_cache = True
        self.support_chunk = True
        self.max_buff_size = 1024 * 1024 * 10

    def bind_runtime(self, name, runtime):
        if not isinstance(runtime, AntRuntime):
            raise ValueError("runtime must be an instance of AntRuntime")
        self.namespace[name] = runtime

    def static_path_root(self, path):
        self.static_path = path

    def upload_path_root(self, path):
        self.upload_path = path

    def script_path_root(self, path):
        self.script_path = path

    def template_path_root(self, path):
        self.template_path = path

    def set_logger(self, logger):
        self.logger = logger

    def set_logger_level(self, level):
        self.logger_level = level


class AntRuntime:
    def __init__(self):
        pass

    def debug(self, msg, *args):
        pass

    def info(self, msg, *args):
        pass

    def warning(self, msg, *args):
        pass

    def error(self, msg, *args):
        pass

    def exception(self, msg, *args):
        pass


class Response:

    def __init__(self):
        self.status_code = 200
        self.msg = ""
        self.headers = {}
        self.cookies = {}
        self.body = io.BytesIO()
        self.version = "HTTP/1.1"

    def set_status(self, code, msg=""):
        self.status_code = code
        if not msg:
            self.msg = RESPONSE_CODE_DEFINED.get(code, "Server Error")
        else:
            self.msg = msg

    def set_header(self, name, value):
        self.headers[name] = value

    def set_cookie(self, name, value, path='/', expires=None):
        self.cookies[name] = f"{name}={value}; Path={path}; Expires={expires}"

    def set_charset(self, charset):
        if "Content-Type" not in self.headers:
            self.headers["Content-Type"] = "text/html; charset={0}".format(charset)
        else:
            self.headers["Content-Type"] += "; charset={0}".format(charset)

    def write(self, text):
        if isinstance(text, str):
            self.body.write(text.encode("utf-8"))
        elif isinstance(text, bytes):
            self.body.write(text)
        else:
            raise ValueError("text must be str or bytes")

    async def send_header(self, session):
        if self.version == "HTTP/0.9":
            return
        session.write("{0} {1} {2}\r\n".format(self.version, self.status_code, self.msg))
        for name, value in self.headers.items():
            session.write("{0}: {1}\r\n".format(name, value))
        if "Content-Type" not in self.headers:
            session.write("Content-Type: text/html; charset=utf-8\r\n")
        if "Date" not in self.headers:
            session.write("{0}: {1}\r\n".format("Date", Utils.to_rfc822(time.localtime())))
        if "Content-Length" not in self.headers:
            session.write("Content-Length: {0}\r\n".format(self.body.tell()))
        for value in self.cookies.values():
            session.write("Set-Cookie: : {0}\r\n".format(value))
        session.write("\r\n")

    async def send_body(self, session):
        session.write_raw(self.body.getvalue())

    def __str__(self):
        return f"Response(status_code={self.status_code}, headers={self.headers}, body={self.body})"


class FileResponse(Response):
    def __init__(self):
        super().__init__()
        self.file_path = None
        self.using_chunk = False
        self.using_range = False
        self.range = None

    def write_with_chunk(self, session):
        with open(self.file_path, "rb") as fp:
            while True:
                chunk = fp.read(Application.ins().max_buff_size)
                if not chunk:
                    self._send_chunk(session, b"")
                    break
                self._send_chunk(session, chunk)

    @staticmethod
    def _send_chunk(session, chunk:bytes):
        chunk_size = len(chunk)
        session.write("%X\r\n" % chunk_size)
        if chunk_size > 0:
            session.write_raw(chunk)
        session.write("\r\n")

    def write_with_range(self, session):
        start_pos = self.range[0]
        size = self.range[1]
        with open(self.file_path, "rb") as fp:
            fp.seek(start_pos, io.SEEK_SET)
            chunk = fp.read(size)
            session.write_raw(chunk)

    async def send_body(self, session):
        if not self.file_path:
            return
        if self.using_range and self.range:
            return self.write_with_range(session)
        if self.using_chunk:
            return self.write_with_chunk(session)
        with open(self.file_path, "r") as fp:
            for line in fp:
                session.write(line)

class Request:
    def __init__(self):
        self.method = "get"
        self.path = "/"
        self.headers = {}
        self.body = None        # type: Buffer or None
        self.version = "HTTP/1.1"
        self.cookies = {}
        self.arguments = {}
        self.files = {}

    def get_header(self, name):
        return self.headers.get(name, None)

    def get_cookie(self, name):
        return self.cookies.get(name, None)

    def get_argument(self, name, default=None):
        return self.arguments.get(name, default)

    def __str__(self):
        return f"Request(method={self.method}, path={self.path})"


class Session:
    # 默认接收数据大小
    DEFAULT_RECV_SIZE = 1024 * 1024
    DEFAULT_MEMORY_SIZE = 1024 * 1024 * 100

    def __init__(self, client_sock:socket.socket):
        super().__init__()
        self.client_sock = client_sock
        self.session_id = uuid.uuid4().hex
        self.close_connection = True
        self.read_fd = client_sock.makefile("rb")
        self.write_fd = client_sock.makefile("wb")
        self.raw_buffer = Buffer(self.session_id, self.DEFAULT_MEMORY_SIZE)

    def read(self, size):
        # 读取指定大小字节的数据
        try:
            return self.read_fd.read(size)
        except Exception as e:
            logging.exception("Error reading data: %s", e)
        return None

    def read_line(self):
        # 读取一行数据
        try:
            line = self.read_fd.readline()
            return line.decode()
        except Exception as e:
            logging.exception("Error reading line: %s", e)
        return None

    def write(self, text:str):
        self.write_fd.write(text.encode("utf-8"))

    def write_raw(self, raw:bytes):
        self.write_fd.write(raw)

    def finish(self):
        self.write_fd.flush()

    def close(self):
        try:
            self.write_fd.close()
            self.read_fd.close()
        except Exception as e:
            logging.exception("Error closing session: %s", e)
        self.client_sock.close()


class RequestParseException(Exception):
    def __init__(self, code, msg):
        super().__init__()
        self.code = code
        self.msg = msg


class SessionHandler:
    # 请求链接处理类
    HTTP_LRE = "\r\n"       # HTTP换行符
    def __init__(self, session:Session):
        self.session = session
        self.request = Request()
        self.close_connection = True

    async def do_handler(self):
        # 处理当前session的请求
        try:
            await self.do_parse()
            await self.do_method()
        except RequestParseException as e:
            await self.do_default_response(e.code, e.msg)

    async def do_method(self):
        route_path = self.request.path
        method_name = self.request.method
        handler_cls = Application.ins().match_route(route_path)
        if handler_cls is None or not issubclass(handler_cls, BaseRequestHandler):
            raise RequestParseException(400, "Bad Request")
        handler = handler_cls(self.session, self.request)
        if not hasattr(handler, method_name):
            raise RequestParseException(405, "Method Not Allowed")
        method = getattr(handler, method_name)
        if not callable(method):
            raise RequestParseException(405, "Method Not Allowed")
        method()
        await self.do_response(handler.response)

    async def do_response(self, response:Response):
        # 处理响应
        if not isinstance(response, Response):
            raise RequestParseException(500, "Server Error")
        try:
            await response.send_header(self.session)
            await response.send_body(self.session)
            self.session.finish()
        except Exception as e:
            logging.exception("Error sending response: %s", e)

    async def do_default_response(self, code, message=""):
        # 处理响应
        if self.request.version == "HTTP/0.9":
            return
        self.session.write("{0} {1} {2}\r\n".format(self.request.version, code, RESPONSE_CODE_DEFINED.get(code, "Server Error")))
        self.session.write("Content-Type: text/html; charset=utf-8\r\n")
        self.session.write("Date: {0}\r\n".format(Utils.to_rfc822(time.localtime())))
        if message:
            self.session.write("Content-Length: {0}\r\n".format(len(message)))
        self.session.write("\r\n")
        self.session.write(message)

    async def do_parse(self):
        # 解析请求头
        await self.parse_method()
        # 非HTTP/0.9的需要解析请求头和请求体
        if self.request.version != "HTTP/0.9":
            await self.parse_header()
            # post 才有请求体
            if self.request.method == "post":
                await self.parse_body()
        # 最后解析参数，因为post的参数在body里面，需要先处理body
        self.do_parse_args()

    async def parse_method(self):
        # 解析请求行  （Request Line）：
        # 方法：如 GET、POST、PUT、DELETE等，指定要执行的操作。
        # 请求 URI（统一资源标识符）：请求的资源路径，通常包括主机名、端口号（如果非默认）、路径和查询字符串。
        # HTTP 版本：如 HTTP/1.1 或 HTTP/2。
        line = self.session.read_line()
        if not line or not line.endswith(self.HTTP_LRE):
            raise RequestParseException(400, "Bad Request")
        params = line.split()
        params_size = len(params)
        # HTTP/0.9
        if params_size == 2:
            method, path = params
            if method.upper() != "GET":
                raise RequestParseException(400, "Bad Request")
            self.request.version = "HTTP/0.9"
        elif params_size == 3:
            method, path, version = params
            if version[0:5] != "HTTP/":
                raise RequestParseException(400, "Bad Request")
            base_version_number = version.split('/', 1)[1]
            version_number = base_version_number.split(".")
            if len(version_number) != 2:
                raise RequestParseException(400, "Bad Request")
            version_number = int(version_number[0]), int(version_number[1])
            # 版本大于等于HTTP/1.1时，支持持续链接
            if version_number >= (1, 1):
                self.session.close_connection = False
            # 目前不支持http/2的版本
            if version_number >= (2, 0):
                raise RequestParseException(400, "Bad Request")
            self.request.version = version.strip()
        else:
            raise RequestParseException(400, "Bad Request")
        self.request.method = method.lower()
        self.request.path = path

    async def parse_header(self):
        # 解析请求头Request Headers）：
        # 包含了客户端环境信息、请求体的大小（如果有）、客户端支持的压缩类型等。
        # 常见的请求头包括Host、User-Agent、Accept、Accept-Encoding、Content-Length等。
        while True:
            line = self.session.read_line()
            if not line or not line.endswith(self.HTTP_LRE):
                raise RequestParseException(400, "Bad Request")
            if line == self.HTTP_LRE:   # 请求头和请求体之间的分隔符，表示请求头的结束。
                break
            index = line.find(":")
            if index < 0:
                raise RequestParseException(400, "Bad Request")
            key = line[0:index].strip().lower()
            value = line[index + 1:].strip()
            self.request.headers[key] = value
        # 解析出Cookie
        self.do_parse_cookies()

    async def parse_body(self):
        # 解析请求体
        # 在某些类型的HTTP请求（如 POST 和 PUT）中，请求体包含要发送给服务器的数据。
        content_length = self.request.get_header("content-length")
        if content_length:  # 前端在请求头里面指定了请求体的大小
            content_length = int(content_length)
            buffer = await self.read_content(content_length)
            if not buffer or not isinstance(buffer, Buffer):
                raise RequestParseException(400, "Bad Request")
            self.request.body = buffer
        else:
            # 前端在请求头里面指定了Transfer-Encoding: chunked，采用chunk上传数据
            tc = self.request.get_header("transfer-encoding")
            if tc and tc.lower() == "chunked":
                buffer = await self.read_chunked()
                if not buffer or not isinstance(buffer, Buffer):
                    raise RequestParseException(400, "Bad Request")
                self.request.body = buffer
            else:
                # 都没有那么就按行读取到结束
                buffer = await self.read_body()
                if not buffer or not isinstance(buffer, Buffer):
                    raise RequestParseException(400, "Bad Request")
                self.request.body = buffer

    async def read_chunked(self):
        # 读取Transfer-Encoding: chunked的请求体
        buffer = Buffer(self.session.session_id)
        while True:
            chunk_size = self.session.read_line()
            if not chunk_size or not chunk_size.endswith(self.HTTP_LRE):
                raise RequestParseException(400, "Bad Request")
            chunk_size = int(chunk_size.strip(), 16)
            if chunk_size == 0:
                return buffer
            data = self.session.read(chunk_size)
            if not data:
                raise RequestParseException(400, "Bad Request")
            buffer.write(data)

    async def read_content(self, content_length:int):
        # 读取Content-Length的请求体
        buffer = Buffer(self.session.session_id)
        while content_length > 0:
            chunk = self.session.read(content_length)
            if not chunk:
                break
            buffer.write(chunk)
            content_length -= len(chunk)
        return buffer

    async def read_body(self):
        # 读取其他的请求体
        buffer = Buffer(self.session.session_id)
        while True:
            line = self.session.read_line()
            if not line:
                break
            buffer.write(line.encode())
        return buffer

    def do_parse_args(self):
        index = self.request.path.find("?")
        if index > 0:
            self.request.path, args = self.request.path.split("?", 1)
            self.parse_args(args)
        if self.request.method == "post":
            self.parse_args()

    def do_parse_cookies(self):
        # 解析cookie
        # 其中cookie的格式为：name1=value1; name2=value2; name3=value3
        cookies = self.request.get_header("cookie")
        if not cookies:
            return
        cookies = cookies.split(";")
        for cookie in cookies:
            k, op, v = cookie.partition("=")
            if op != "=":
                continue
            self.request.cookies[k.strip()] = v.strip()

    def parse_args(self, url_args=None):
        if url_args:
            args = urllib.parse.parse_qs(url_args, keep_blank_values=True)
            self.request.arguments.update(args)
        # 如果请求体是空的，则不需要解析
        buffer = self.request.body
        if not buffer:
            return
        # 解析表单参数
        # application/x-www-form-urlencoded 格式 与URL参数一样
        # multipart/form-data 格式则比较特殊
        # Content-Type: text/html; charset=utf-8
        # Content-Type: multipart/form-data; boundary=something
        content_type = self.request.get_header("content-type")
        if not content_type:
            return
        ctype, params = cgi.parse_header(content_type)
        if ctype == "multipart/form-data":
            boundary = params.get("boundary")
            if not boundary:
                return
            self.parse_multipart_form_data(buffer, boundary)
        elif ctype == "application/x-www-form-urlencoded":
            # 这种格式的请求体和URL参数一样 因此不会有太大的数据量，直接读取操作
            args = urllib.parse.parse_qs(buffer.get_value().decode(), keep_blank_values=True)
            self.request.arguments.update(args)

    def parse_sub_header(self, headers):
        """
        解析请求头数据
        :param headers:
        :return:
        """
        headers_re = {}
        for line in self.HTTP_LRE.split(headers):
            key, args = line.split(":")
            headers_re[key] = args
        return headers_re

    def parse_multipart_form_data(self, buffer:Buffer, boundary):
        # # 请求头 - 这个是必须的，需要指定Content-Type为multipart/form-data，指定唯一边界值
        # Content-Type: multipart/form-data; boundary=${Boundary}
        #
        # # 请求体
        # --${Boundary}
        # Content-Disposition: form-data; name="name of file"
        # Content-Type: application/octet-stream
        #
        # bytes of file
        # --${Boundary}
        # Content-Disposition: form-data; name="name of pdf"; filename="pdf-file.pdf"
        # Content-Type: application/octet-stream
        #
        # bytes of pdf file
        # --${Boundary}
        # Content-Disposition: form-data; name="key"
        # Content-Type: text/plain;charset=UTF-8
        #
        # text encoded in UTF-8
        # --${Boundary}--
        boundary = boundary.encode("utf-8")
        if boundary.startswith(b'"') and boundary.endswith(b'"'):
            boundary = boundary[1:-1]

        split_boundary = b"--" + boundary           # 读取multipart/form-data的开始边界
        final_boundary = b"--" + boundary + b"--"        # 读取multipart/form-data的结束边界
        while True:
            line = buffer.readline()
            if not line or not line.startswith(split_boundary):
                continue
            # 返回False表示已经读取到最后一项数据了
            if not self.parse_single_multipart_form_data(buffer, split_boundary, final_boundary):
                break

    @staticmethod
    def parse_multipart_form_head(data:str):
        # form-data的头内容解析
        # Content-Disposition: form-data; name="name of pdf"; filename="pdf-file.pdf"
        # Content-Type: application/octet-stream
        headers = {}
        for i, item in enumerate(data.split(";")):
            if i == 0:
                kv = item.split(":")
            else:
                kv = item.split("=")
            if len(kv) == 2:
                headers[kv[0].strip().lower()] = kv[1].strip()
        return headers

    @staticmethod
    def read_multipart_form_value(buffer:Buffer, value, boundary:bytes):
        # 读取multipart/form-data的值
        while True:
            line = buffer.readline()
            if line.startswith(boundary):
                return line
            value.write(line)

    def parse_single_multipart_form_data(self, buffer:Buffer, split_boundary:bytes, final_boundary:bytes):
        # 读取multipart/form-data中单项数据内容

        form_headers = {}   # 读取multipart/form-data的头
        while True:
            line = buffer.readline().decode("utf-8")
            if line.startswith(self.HTTP_LRE):  # 读取结束
                break
            headers = self.parse_multipart_form_head(line)
            form_headers.update(headers)

        # Content-Disposition: form-data; name="${PART_NAME}"; 必须包含，用于指定接下来的请求体的名称
        disposition = form_headers.get("content-disposition", "")
        name = form_headers.get("name", "")
        if not disposition or not name or not disposition.startswith("form-data"):
            raise RequestParseException(400, "Bad Request")
        # 只有文件才会有这个字段
        filename = form_headers.get("filename", "")
        if not filename:
            # 不是文件，则直接读取出里面的内容
            value = io.BytesIO()
            line = self.read_multipart_form_value(buffer, value, split_boundary)
            self.request.arguments[value] = value.getvalue().decode("utf-8")
            if line.startswith(final_boundary): # 结束
                return False
            return True
        # 是文件，则需要保存到临时文件中
        temp_file_path = os.path.join(Application.ins().upload_path, filename)
        value = Buffer(temp_file_path)
        line = self.read_multipart_form_value(buffer, value, split_boundary)
        #.setdefault(name, []).append(http_file) 暂时去掉同name的支持
        self.request.files[name] = UploadFile(filename, form_headers.get("content-type"), value)
        if line.startswith(final_boundary): # 结束
            return False
        return True


class BaseRequestHandler:
    def __init__(self, session:Session, request:Request):
        self.session = session
        self.request = request
        self.response = None

    def write(self, body:str):
        self.response.write(body)

    def write_error(self, code, msg="", body=""):
        self.response.set_status(code, msg)
        self.write(body)


class RequestHandler(BaseRequestHandler):
    def __init__(self, session:Session, request:Request):
        super().__init__(session, request)
        self.response = Response()


class StaticFileHandler(BaseRequestHandler):
    # 下载静态文件

    def __init__(self, session:Session, request:Request):
        super().__init__(session, request)
        self.response = FileResponse()

    def head(self):
        """
        head 请求
        :return:
        """
        return self.get(include_body=False)

    def do_cache_request(self, file_path, size, use_range=None):
        """
        执行缓存请求
        :param file_path:
        :param size:
        :param use_range:
        :return:
        """
        support_static_cache = Application.ins().static_cache
        support_chunk = Application.ins().chunk_support
        max_buff_size = Application.ins().max_buff_size
        if support_static_cache:
            if_modify_date = self.request.get_header("If-Modified-Since")
            cache_control = self.request.get_header("Cache-control")
            if not cache_control or cache_control.find("no-cache") < 0:
                file_modify_date = self.file_modify_date(file_path)
                if if_modify_date and if_modify_date == file_modify_date and not use_range:
                    self.response.set_status(304)
                    return
                self.response.set_header("Cache-control", "no-cache")
                if not use_range:
                    self.response.set_header("Last-Modified", file_modify_date)
        if not support_static_cache or not use_range:
            if not support_chunk:
                self.response.set_header("Content-Length", size)
            else:
                self.response.set_header("Transfer-Encoding", "chunked")
            self.response.using_chunk = support_chunk
        else:
            start, end = use_range
            # Range: -1024表示从资源末尾往前读取1024个字节的内容
            if start is None:
                start = size - end
            # Range: 0- 表示从资源开始到末尾，为了防止资源过大，这里并不一定需要一次性将全部读取返回
            if end is None:
                end = size - 1
            read_size = end - start + 1
            if read_size > max_buff_size:
                read_size = max_buff_size
                end = read_size + start - 1
            self.response.set_header("Content-Range", "bytes %s-%s/%s" % (start, end, size))
            self.response.set_header("Content-Length", read_size)
            self.response.set_status(206)
            self.response.using_range = True
            self.response.range = [start, read_size]

    def get(self, include_body=True):
        """
        静态文件get请求
        :param include_body:
        :return:
        """
        file_path = self.get_file_path()
        if not file_path:
            return self.write_error(404, "", "%s is not exist" % file_path)
        # 如果不是允许下载的格式，则返回403
        minetype = self.get_file_mime_type(file_path)
        if not minetype:
            return self.write_error(403)
        if include_body:
            self.response.file_path = file_path
        # 获取文件的总大小
        size = os.path.getsize(file_path)
        # 设置响应头，表示服务器支持Range格式请求
        if Application.ins().static_cache:
            self.response.set_header("Accept-Ranges", "bytes")
        self.response.set_header("Content-Type", minetype)
        # 检查客户端的请求中是否采样Range格式请求
        range_header = self.request.get_header("Range")
        if not range_header:
            self.do_cache_request(file_path, size)
        else:
            start, end = self.parse_range(range_header)
            # 需要读取的起始位置不能为空，或者超出了文件的大小
            if (start is None and end is None) or \
                    (start is not None and start >= size) or \
                    (end is not None and end >= size):
                self.response.set_header("Content-Range", "bytes */%s" % (size,))
                self.write_error(416)
                return
            self.do_cache_request(file_path, size, use_range=[start, end])

    def get_file_path(self):
        """
        获取文件的路径
        """
        # 对url进行解码，有可能有带空格的文件之类的
        path = urllib.parse.unquote(self.request.path)
        if not path.startswith("/static"):
            return None
        path = path[len("/static"):]
        url_route_path = path if not path.startswith("/") else path[1:]
        file_path = os.path.join(Application.ins().static_path, url_route_path)
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
        return Utils.to_rfc822(file_mt)

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
        start = Utils.int_or_none(start_b)
        end = Utils.int_or_none(end_b)

        if end is not None:
            if start is None:
                if end != 0:
                    start = -end
                    end = None
            else:
                end += 1
        return start, end

    @staticmethod
    def get_file_mime_type(filename):
        """ 根据文件扩展名获取文件类型 """
        dot_index = filename.rfind(".")
        if dot_index < 0:
            return "application/octet-stream"
        return MINE_TYPE_DEFINED.get(filename[dot_index:], "application/octet-stream")


class HttpServer:
    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.selector = selectors.DefaultSelector()
        self.server_socket = None
        self.routes = {}
        self.session_map = {}

    def create_server_socket(self):
        # 启动HTTP服务器
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.selector.register(self.server_socket, selectors.EVENT_READ, self.accept)
        logging.debug(f"Server started at {self.host}:{self.port}")

    def start(self):
        self.create_server_socket()
        asyncio.run(self.server_loop())

    async def server_loop(self):
        try:
            while True:
                events = self.selector.select(timeout=0.1)
                for key, _ in events:
                    callback = key.data
                    callback(key.fileobj)
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logging.debug("Server shutting down...")
        finally:
            self.server_socket.close()

    def accept(self, server_socket):
        try:
            client_socket, addr = server_socket.accept()
            logging.debug(f"Connection from {addr}")
            client_socket.setblocking(False)
            self.selector.register(client_socket, selectors.EVENT_READ, self.read)
        except Exception as e:
            logging.exception(f"Error accepting connection: {e}")

    def read(self, client_socket):
        self.selector.unregister(client_socket)
        session = self.session_map.get(client_socket, None)
        if session is None:
            session = Session(client_socket)
            self.session_map[client_socket] = session
        loop = asyncio.get_event_loop()
        loop.create_task(self.handle_session(session))

    async def handle_session(self, session:Session):
        handler = SessionHandler(session)
        await handler.do_handler()
        if handler.close_connection:
            session.close()
            logging.debug(f"Session {session.session_id} closed")
            self.session_map.pop(session.client_sock)
        else:
            self.selector.register(session.client_sock, selectors.EVENT_READ, self.read)


class HttpSSLServer(HttpServer):
    def __init__(self, host, port, certfile, keyfile):
        super().__init__(host, port)
        self.certfile = certfile
        self.keyfile = keyfile

    def create_server_socket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket = ssl.wrap_socket(self.server_socket, certfile=self.certfile, keyfile=self.keyfile, server_side=True)
        logging.info(f"SSL Server started at {self.host}:{self.port}")


class Application:
    # 单例对象
    _instance = None

    @staticmethod
    def ins():
        if Application._instance is None:
            Application._instance = Application()
        return Application._instance

    def __init__(self):
        super().__init__()
        self.config = None  # type: HttpConfig or None
        self.routes = {}

    @property
    def static_cache(self):
        return self.config.support_static_cache

    @property
    def chunk_support(self):
        return self.config.support_chunk

    @property
    def static_path(self):
        return self.config.static_path

    @property
    def upload_path(self):
        return self.config.upload_path

    @property
    def max_buff_size(self):
        return self.config.max_buff_size

    def add_route(self, path, handler_cls):
        if not issubclass(handler_cls, BaseRequestHandler):
            raise ValueError("handler_cls must be a subclass of BaseRequestHandler")
        self.routes[path] = handler_cls

    def match_route(self, path):
        if path.startswith("/static"):
            return StaticFileHandler
        return self.routes.get(path, None)

    def start_server(self, config:HttpConfig, host="127.0.0.1", port=8080):
        self.config = config
        server = HttpServer(host, port)
        server.start()


def route(path):
    # 装饰器 绑定路由
    def decorator(cls):
        Application.ins().add_route(path, cls)
        return cls
    return decorator


def start_server(config:HttpConfig, host="127.0.0.1", port=8080):
    # 启动HTTP服务器
    Application.ins().start_server(config, host, port)
