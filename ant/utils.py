# -*- coding:utf-8 -*-
import time
import urllib.parse


def int_or_none(value):
    # 返回一个整数，如果值为None或无法转换为整数，则返回None
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def to_rfc822(time_local, zone=None):
    # 将本地时间转换为RFC 822格式的字符串
    if zone is None:
        zone = "GMT"
    return time.strftime('%a, %d %b %Y %H:%M:%S {0}'.format(zone), time_local)


def exec_code(code, glob, loc=None):
    # 执行给定的代码字符串
    if isinstance(code, str):
        code = compile(code, '<string>', 'exec', dont_inherit=True)
    exec(code, glob, loc)


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


def html_escape(data):
    # 将数据进行HTML转义
    if isinstance(data, str):
        return data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#039;")
    return data


def url_args_parse(url_args, **kwargs):
    # 解析URL参数,返回参数字典
    return urllib.parse.parse_qs(url_args, **kwargs)


def url_unquote(url, encoding='utf-8', errors='replace'):
    # 反转义URL
    return urllib.parse.unquote(url, encoding, errors)
