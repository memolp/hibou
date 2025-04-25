# -*- coding:utf-8 -*-


# Http请求对象
class Request:
    def __init__(self):
        self.method = "get"
        self.path = "/"
        self.headers = {}
        self.body = None
        self.version = "HTTP/1.1"
        self.cookies = {}
        self.arguments = {}
        self.files = {}

    def get_param(self, name):
        pass

    def get_header(self, name):
        return self.headers.get(name, None)

    def get_headers(self):
        return self.headers

    def get_params(self):
        pass

    def get_cookies(self):
        pass

    def get_cookie(self, name):
        pass

    def get_files(self):
        pass

    def __str__(self):
        return f"Request(method={self.method}, path={self.path}, headers={self.headers}, body={self.body})"

