# -*- coding: utf-8 -*-

# Http响应对象
class Response:
    def __init__(self, status_code, headers, body):
        self.status_code = status_code
        self.headers = headers
        self.body = body

    def set_header(self, name, value):
        self.headers[name] = value

    def set_cookie(self, name, value, path='/', expires=None):
        self.headers['Set-Cookie'] = f"{name}={value}; Path={path}; Expires={expires}"

    def __str__(self):
        return f"Response(status_code={self.status_code}, headers={self.headers}, body={self.body})"

