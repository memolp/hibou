# -*- coding:utf-8 -*-

"""
打包成一个whl包
1. 先编译为pyd文件
2. 将pyd文件和其他依赖的py文件打包成whl包
"""

from setuptools import setup

# 如果要加一个目录，就需要这样操作，里面的内容可以参考PyQt5的组织方式，
# 导入就需要from xxx import 对应的模块， 放在__init__.py 外部使用的时候无法获得pyi的提示功能。
setup(
    name='hibou',
    version='1.0.1',
    packages=['hibou_web'],
    install_requires=[],  # 如果有依赖，添加在这里
    include_package_data=True,
    package_data={
        'hibou_web': ['*.pyd', '*.pyi'],  # 确保 .pyd 和 .pyi 文件被包含
    },
)
