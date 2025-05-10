rem 将准备的包生成whl
rem sdist 是用来构建源码分发包，即 .tar.gz 这种格式
rem bdist_wheel 是创建一个 whl 分发包
python setup.py sdist bdist_wheel