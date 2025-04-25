# -*- coding:utf-8 -*-

from .application import Application
from .handler import RequestHandler

# 模块单例对象
app = None    # type: Application or None


def route(path):
    def decorator(func):
        app.add_route(path, func)
        return func
    return decorator


def _init_module():
    global app
    if app is None:
        app = Application()

_init_module()


