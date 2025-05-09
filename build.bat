rem 将原文件生成ide可以自动提示的说明文件
rem 需要安装pip install mypy
stubgen hibou.py -o .

rem 将原文件打包成pyd
rem 需要安装pip install Cython
python setup.py build_ext --inplace
