# -*- coding:utf-8 -*-

"""
将ant打包成一个whl包
1. 先将ant编译为pyd文件
2. 将pyd文件和其他依赖的py文件打包成whl包
"""

import sys

from setuptools import setup, find_packages
from Cython.Build import cythonize

if "build_ext" in sys.argv:
    setup(
        name="hibou",
        version="1.0.0",
        author="Jeff Xun",
        ext_modules= cythonize("hibou.py"))

else:
    setup(
        name='hibou',
        version='0.1',
        packages=find_packages(),
        install_requires=[],  # 如果有依赖，添加在这里
        package_data={
            'hibou': ['*.pyd', '*.pyi'],  # 确保 .pyd 和 .pyi 文件被包含
        },
        include_package_data=True,
    )