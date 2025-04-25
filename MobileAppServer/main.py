# -*- coding:utf-8 -*-

"""
项目真机包下载平台，需要支持账号登录，支持下载的权限设置

pip install ant-web
pip isntall ant-web --no-index --find-links=.\ant-web
pip install pymysql
"""

import ant
import pymysql

class MysqlOO(ant.Runtime):
    pass


app = ant.Application()
app.bind_runtime("db", MysqlOO)
app.static_path_root("static")
app.upload_path_root("static/upload files")
app.script_path_root("handlers")
app.template_path_root("templates")
app.start_server()


