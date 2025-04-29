rem 将原文件生成ide可以自动提示的说明文件
rem stubgen hibou.py -o .

rem 将原文件打包成pyd
rem python setup.py build_ext --inplace

rem 将准备的包生成whl
python setup.py sdist bdist_wheel