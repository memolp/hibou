# -*- coding:utf-8 -*-

"""
项目真机包下载平台，需要支持账号登录，支持下载的权限设置

pip install hibou-web
pip isntall hibou-web --no-index --find-links=.\hibou-web
pip install pymysql
"""

import hibou
import pymysql
import logging

# class MysqlOO(hibou.Runtime):
#     pass


logging.basicConfig(level=logging.DEBUG)


conf = hibou.HttpConfig()
# conf.bind_runtime("db", MysqlOO)
conf.static_path_root("static")
conf.upload_path_root("static/upload files")
conf.script_path_root("handlers")
conf.template_path_root("templates")

hibou.start_server(conf, "0.0.0.0", 8000)


