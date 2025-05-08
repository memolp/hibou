# -*- coding:utf-8 -*-

"""
将ant打包成一个whl包
1. 先将ant编译为pyd文件
2. 将pyd文件和其他依赖的py文件打包成whl包
"""


from setuptools import setup

# 下面这种是直接放在根目录
setup(
    name="hibou",
    version="1.0.1",
    py_modules=["hibou"],   # 表示是“顶层模块”
    data_files=[("", ["hibou.cp37-win_amd64.pyd", "hibou.pyi"])],  # 安装到 site-packages 根目录,
)