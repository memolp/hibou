# -*- coding:utf-8 -*-

"""
将ant打包成一个whl包
1. 先将ant编译为pyd文件
2. 将pyd文件和其他依赖的py文件打包成whl包
"""

from setuptools import setup
from Cython.Build import cythonize

setup(
    name="hibou",
    version="1.0.0",
    author="Jeff Xun",
    ext_modules= cythonize("hibou.py"))

