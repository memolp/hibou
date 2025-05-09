# 目录说明
这里用于将hibou打包成顶层的whl包。<br>
1. 需要执行外部的build.bat将hibou.py编译未hibou.pyd
2. 然后将生成pyd和pyi拷贝到这个目录里面来。
3. setup.py和MANIFEST.in里面pyd的文件名一定要确认正确才可以。
4. 执行这个目录的build.bat就可以在dist目录里面获得可安装的whl包。

# 这个包安装后的使用
```python

import hibou

conf = hibou.HttpConfig()
conf.static_path_root("static")   # 设置静态资源的路径
conf.script_path_root("scripts")  # 设置脚本的目录
conf.template_path_root("templates")    # 设置HTML模板文件的目录
hibou.start_server(conf, "0.0.0.0", 7000)  # 启动HTTP服务

```