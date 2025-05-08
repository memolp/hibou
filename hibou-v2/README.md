# 目录说明
这里使用将hibou打包成一个带有模块目录的whl<br>
1. 将外部编译好的pyd和pyi放到`hibou_web`目录. 如果当前目录下没有`hibou_web`目录就创建一个。
2. 执行这个目录的build.bat 就可以得到一个whl包
3. hibou_web这个模块包名可以随便取其他的名字，最终使用的方式取决from import
4. 如果在hibou_web里面的__init__.py里面写入from hibou import xx之后也可以直接使用hibou_web.xx使用，但是会丢失IDE的参数提示。

# 这个包安装后的使用
```python

from hibou_web import hibou

conf = hibou.HttpConfig()
conf.static_path_root("static")   # 设置静态资源的路径
conf.upload_path_root("static/upload files")  # 设置上传文件的保存路径
conf.script_path_root("scripts")  # 设置脚本的目录
conf.template_path_root("templates")    # 设置HTML模板文件的目录
hibou.start_server(conf, "0.0.0.0", 7000)  # 启动HTTP服务

```