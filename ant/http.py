# -*- coding:utf-8 -*-

import socket,selectors,ssl
import asyncio

from .buffer import Buffer
from .request import Request
from .session import Session
from .multipart import UploadFile


class HttpServer:

    HTTP_LRE = "\r\n"

    def __init__(self, app:AntRuntime, host='127.0.0.1', port=8080):
        self.logger = app
        self.host = host
        self.port = port
        self.selector = selectors.DefaultSelector()
        self.server_socket = None
        self.routes = {}

    def start(self):
        # 启动HTTP服务器
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.selector.register(self.server_socket, selectors.EVENT_READ, self.accept)
        self.logger.debug(f"Server started at {self.host}:{self.port}")
        try:
            while True:
                events = self.selector.select()
                for key, _ in events:
                    callback = key.data
                    callback(key.fileobj)
        except KeyboardInterrupt:
            self.logger.debug("Server shutting down...")
        finally:
            self.server_socket.close()

    def accept(self, server_socket):
        try:
            client_socket, addr = server_socket.accept()
            self.logger.debug(f"Connection from {addr}")
            client_socket.setblocking(False)
            self.selector.register(client_socket, selectors.EVENT_READ, self.read)
        except Exception as e:
            self.logger.exception(f"Error accepting connection: {e}")

    def read(self, client_socket):
        session = Session(client_socket, Request())
        asyncio.create_task(self.handle_session(session))

    def close_session(self, session):
        self.selector.unregister(session.client_sock)
        session.close()
        self.logger.debug(f"Session {session.session_id} closed")

    async def handle_session(self, session:Session):
        # 处理当前session的请求
        # 解析请求头
        result = await self.parse_method(session)
        if not result:
            self.close_session(session)
            return
        # 非HTTP/0.9的需要解析请求头和请求体
        if session.version != "HTTP/0.9":
            result = await self.parse_header(session)
            if not result:
                self.close_session(session)
                return
            # post 才有请求体
            if session.method == "post":
                result = await self.parse_body(session)
                if not result:
                    self.close_session(session)
                    return
        response = await self.do_method(session)
        if not response:
            self.close_session(session)
            return
        session.send(response.decode())
        # 如果不保持连接，则关闭连接
        if session.close_connection:
            self.close_session(session)

    async def parse_method(self, session:Session):
        line = session.read_line()
        if not line or not line.endswith(self.HTTP_LRE):
            session.send_error(400, "Bad Request")
            return False
        params = line.split()
        params_size = len(params)
        # HTTP/0.9
        if params_size == 2:
            method, path = params
            if method.upper() != "GET":
                session.send_error(400, "Bad Request")
                return False
            session.version = "HTTP/0.9"
        elif params_size == 3:
            method, path, version = params
            if version[0:5] != "HTTP/":
                session.send_error(400, "Bad Request")
                return False
            try:
                base_version_number = version.split('/', 1)[1]
                version_number = base_version_number.split(".")
                if len(version_number) != 2:
                    raise ValueError
                version_number = int(version_number[0]), int(version_number[1])
            except Exception as e:
                    session.send_error(400, "Bad Request")
                    return False
            # 版本大于等于HTTP/1.1时，支持持续链接
            if version_number >= (1, 1):
                session.close_connection = False
            # 目前不支持http/2的版本
            if version_number >= (2, 0):
                session.send_error(400, "Bad Request")
                return False
            session.version = version.strip()
        else:
            session.send_error(400, "Bad Request")
            return False
        session.method = method.lower()
        session.path = path
        return True

    async def parse_header(self, session:Session):
        while True:
            line = session.read_line()
            if not line or not line.endswith(self.HTTP_LRE):
                session.send_error(400, "Bad Request")
                return False
            if line == self.HTTP_LRE:
                break
            index = line.find(":")
            if index < 0:
                session.send_error(400, "Bad Request")
                return False
            key = line[0:index].strip().lower()
            value = line[index + 1:].strip()
            session.request.headers[key] = value
        return True

    async def parse_body(self, session:Session):
        content_length = session.request.get_header("content-length")
        if content_length:
            try:
                content_length = int(content_length)
                buffer = await self.read_content(session, content_length)
                if not buffer:
                    session.send_error(400, "Bad Request")
                    return False
                session.request.body = buffer
                return True
            except Exception as e:
                session.send_error(400, "Bad Request")
                return False
        else:
            tc = session.request.get_header("transfer-encoding")
            if tc and tc.lower() == "chunked":
                buffer = await self.read_chunked(session)
                if not buffer:
                    session.send_error(400, "Bad Request")
                    return False
                session.request.body = buffer
                return True
            else:
                buffer = await self.read_body(session)
                session.request.body = buffer
                return True

    async def read_chunked(self, session:Session):
        while True:
            chunk_size = session.read_line()
            if not chunk_size or not chunk_size.endswith(self.HTTP_LRE):
                session.send_error(400, "Bad Request")
                return False
            try:
                chunk_size = int(chunk_size.strip(), 16)
            except ValueError:
                session.send_error(400, "Bad Request")
                return False
            if chunk_size == 0:
                return True
            if not session.read(chunk_size):
                session.send_error(400, "Bad Request")
                return False

    async def read_content(self, session:Session, content_length:int):
        buffer = Buffer(session.session_id)
        while content_length > 0:
            chunk = session.read(content_length)
            if not chunk:
                break
            buffer.write(chunk)
            content_length -= len(chunk)
        return buffer

    async def read_body(self, session:Session):
        buffer = Buffer(session.session_id)
        while True:
            line = session.read_line()
            if not line:
                break
            buffer.write(line.encode())
        return buffer

    async def do_method(self, session:Session):
        try:
            self.do_parse_args(session.request)
            self.do_parse_cookies(session.request)
            handler_cls = self.routes.get(session.path)
            if not handler_cls:
                session.send_error(404, "Not Found")
                return
            handler = handler_cls(session.request)
            if not hasattr(handler, session.method):
                session.send_error(405, "Method Not Allowed")
                return
            method = getattr(handler, session.method)
            if not callable(method):
                session.send_error(405, "Method Not Allowed")
                return
            method()
            return handler.response()
        except Exception as e:
            pass

    def do_parse_args(self, request:Request):
        try:
            index = request.path.find("?")
            if index > 0:
                request.path, args = request.path.split("?", 1)
                self.parse_args(request, args)
            if request.method == "post":
                self.parse_args(request)
            return True
        except Exception as e:
            return False

    def do_parse_cookies(self, request:Request):
        try:
            cookies = request.get_header("cookie")
            if not cookies:
                return
            cookies = cookies.split(";")
            for cookie in cookies:
                k, op, v = cookie.partition("=")
                if op != "=":
                    continue
                request.cookies[k.strip()] = v.strip()
        except Exception as e:
            return

    def parse_args(self, request:Request, url_args=None):
        if url_args:
            args = parse_qs(url_args, keep_blank_values=True)
            request.arguments.update(args)
        if not request.body:
            return
        content_type = request.get_header("content-type")
        if not content_type:
            return
        ctype, params = cgi.parse_header(content_type)
        if ctype == "multipart/form-data":
            boundary = params.get("boundary")
            if not boundary:
                return
            self.parse_multipart_form_data(request, boundary)
        elif ctype == "application/x-www-form-urlencoded":
            args = parse_qs(request.body.decode(), keep_blank_values=True)
            request.arguments.update(args)

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

    def parse_multipart_form_data(self, request:Request, boundary):
        #TODO: 解析multipart/form-data body是buffer，需要改读取数据方式
        raw_data = request.body
        boundary = boundary.encode()
        if boundary.startswith(b'"') and boundary.endswith(b'"'):
            boundary = boundary[1:-1]
        final_boundary_index = raw_data.rfind(b"--" + boundary + b"--")
        if final_boundary_index == -1:
            # logging.error("[multipart_form_data] %s no final boundary", self.client)
            return -1
        parts = raw_data[:final_boundary_index].split(b"--" + boundary + b"\r\n")
        for part in parts:
            if not part:
                continue
            eoh = part.find(b"\r\n\r\n")
            if eoh == -1:
                # logging.error("[multipart_form_data] %s missing headers", self.client)
                return -1
            headers = self.parse_sub_header(part[:eoh].decode("utf-8"))
            dis_header = headers.get("Content-Disposition", "")
            disposition, disp_params = cgi.parse_header(dis_header)
            if disposition != "form-data" or not part.endswith(b"\r\n"):
                # logging.error("[multipart_form_data] %s format error", self.client)
                return -1
            value = part[eoh + 4:-2]
            if not disp_params.get("name"):
                # logging.error("[multipart_form_data] %s value missing name", self.client)
                return -1
            name = disp_params["name"]
            if disp_params.get("filename"):
                mine_type = headers.get("Content-Type", "application/unknown")
                http_file = UploadFile(filename=disp_params["filename"], filetype=mine_type, filedata=value)
                request.files.setdefault(name, []).append(http_file)
            else:
                request.arguments.setdefault(name, []).append(value.decode())
        return 0


# 支持SSL的Ant Web服务类
class HttpSSLServer(HttpServer):
    def __init__(self, app, host, port, certfile, keyfile):
        super().__init__(app, host, port)
        self.certfile = certfile
        self.keyfile = keyfile

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket = ssl.wrap_socket(self.server_socket, certfile=self.certfile, keyfile=self.keyfile, server_side=True)
        print(f"SSL Server started at {self.host}:{self.port}")

        loop = asyncio.get_event_loop()
        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                print(f"SSL Connection from {addr}")
                loop.create_task(self.handle_session(client_socket))
        except KeyboardInterrupt:
            print("SSL Server shutting down...")
        finally:
            self.server_socket.close()
