# -*- coding:utf-8 -*-

"""
打包成一个whl包
1. 先编译为pyd文件
2. 将pyd文件和其他依赖的py文件打包成whl包
"""

import setuptools

# 下面这种是直接放在根目录
setuptools.setup(
    name="hibou",           # 打包后生成的文件名，会以这个name为前缀
    version="1.0.1",        # 版本 =>  hibou-1.0.1-py4-none-any.whl
    author="qingf",         # 作者
    author_email="memolp@163.com",  # 作者邮箱
    description="一个简单的web服务框架",     # 描述
    # 我这里就很简单不需要包含其他的包
    # packages=setuptools.find_packages(),        # 自动查找当前项目下的所有包。譬如当前项目有 'demos', 'pipmodule' 两个包，这样这两个包都会被打包进最终生成的模块中。
    url="https://github.com/memolp/hibou",      # 项目地址
    # 配置元数据信息 更多内容参见：https://pypi.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",  # 项目开发阶段
        "Programming Language :: Python :: 3",  # 编程语言
        "License :: OSI Approved :: MIT License",  # license
        "Operating System :: OS Independent",  # 操作系统
    ],
    # 当前项目的依赖，比如当前项目依赖了 requests 库，当按照当前的模块时，会自动把 requests 也安装上
    install_requires = [
        # "requests",
        # "pytest>=3.3.1",  # 也可以出依赖的具体版本
    ],
    # package_data 可以将一些静态的包内的文件，打包进你的模块中，文件支持通配符的方式，如：{"package_name": ["*.txt", "*.jpg"]}
    # package_data={"package_name": ["*.txt"]},
    # exclude_package_data 可以排除一些包内的文件
    # exclude_package_data={'你的包名':['*.txt']}
    # 设置当前项目适用的 python 版本：3，也可以写成支持多个版本的范围：">=2.7, <=3"
    python_requires = ">=3",
    # include_package_data 设为 True 时，它会自动打包包中已经受到版本控制的文件
    # 某些方面可以替代 package_data 这个参数（没有进行版本控制的文件，依然要使用 package_data 这个选项来添加）
    include_package_data=True,

    py_modules=["hibou"],   # 表示是“顶层模块”
    # 这个选项可以设置一些本地的源文件，当用户安装这个模块时，会自动将 "源文件" 复制到到 ”要安装的地方“
    # data_files = [("要安装到哪儿1", "源文件1"), ("要安装到哪儿2", "源文件2"), ...]  这是一种格式
    # data_files = [("安装到哪", ["文件1", "文件2"])]  这种格式也是支持的
    data_files=[("./Lib/site-packages", ["hibou.cp37-win_amd64.pyd", "hibou.pyi"])],  # 安装到 site-packages 根目录,
)

# MANIFEST.in
# 你还可以创建一个和 setup.py 同级的配置文件：MANIFEST.in ,它可以配置文件的分发，setup.py 会自动读取它。举例：
# include *.txt     说明： 会包含所有的 txt 文件
# recursive-include demos *.txt *.jpg *.py  说明： 会递归查询 demos 和子目录，以及所有的 txt，jpg，py 文件
# prune demos/sample?/build  说明： 排除匹配 demos/sample?/build 的路径