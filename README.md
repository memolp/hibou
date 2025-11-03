# hibou 简单HTTP服务
一个简单的Python语言写的Http服务器，学习了其他的框架的，然后尝试自己实现的一个框架，可以理解他是一个玩具，代码简单方便快速使用。
我主要用它可以搭建一些团队内部使用的平台工具。<br>
里面使用了协程+多线程的方式处理请求，支持模板渲染页面，支持GET和POST请求，<br>
POST方法支持`application/x-www-form-urlencoded`和`multipart/form-data`的表单提交，支持上传大型文件，使用流式解析处理。


# 如何使用
如果直接将hibou.py放入项目工程就可以直接`import hibou`就可以使用。<br>
也可以打包成whl包安装到python的库目录，然后使用 `import hibou` 或者 `from xxx import hibou` 来使用。
### 简单列子

#### 启动HTTP服务
```python

import hibou    # 导入模块

conf = hibou.HttpConfig()
conf.static_path_root("static")   # 设置静态资源的路径
conf.script_path_root("scripts")  # 设置脚本的目录
conf.template_path_root("templates")    # 设置HTML模板文件的目录
hibou.start_server(conf, "0.0.0.0", 7000)  # 启动HTTP服务
```
上面启动服务后并没有任何处理，当然如果static目录有内容则可以通过http://127.0.0.1:7000/static/xxx.js访问。<br>
#### 添加路由处理
1. 在scripts目录里面创建py脚本
2. 里面import hibou 然后编写路由类
```python
import hibou

# 访问http://127.0.0.1:7000/  会返回Hello World!!
@hibou.route("/")
class IndexHandler(hibou.RequestHandler):
    def get(self):
        return self.write("Hello World!!")

# 如果在templates目录里面有一个login.html的模板，就可以使用render直接渲染这个模板给客户端
# http://127.0.0.1:7000/login 就可以看到效果。
# 模板语言 来自 tornado
@hibou.route("/login")
class LoginHandler(hibou.RequestHandler):
    def get(self):
        return self.render("login.html")
```

# 性能测试
```python
@hibou.route("/")
class IndexHandler(hibou.RequestHandler):
    def get(self):
        return self.write("Hello World!!")
```
这种简单的文本发送使用wrk测试的结果,每秒可以处理2000个请求，1分钟处理10万请求。反正我够用了。
```commandline
./wrk -c 10 -t 2 -d 60 http://127.0.0.1/
Running 1m test @ http://127.0.0.1/
  2 threads and 10 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     3.47ms  624.71us  14.83ms   77.70%
    Req/Sec     1.23k    55.86     1.42k    78.88%
  146827 requests in 1.00m, 18.20MB read
  Socket errors: connect 0, read 146826, write 0, timeout 0
Requests/sec:   2446.49
Transfer/sec:    310.59KB
```

```python
@hibou.route("/")
class IndexHandler(hibou.RequestHandler):
    def get(self):
        return self.render("index.html")
```
这种需要进行模板渲染的，我没有优化模板渲染，每次调用render都是重新读取文件处理，没有使用缓存。
每秒可以处理1000的请求，已经满足我平常使用了。
```commandline
./wrk -c 100 -t 2 -d 60 http://127.0.0.1/
Running 1m test @ http://127.0.0.1/
  2 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    94.88ms    6.92ms 152.02ms   88.34%
    Req/Sec   524.64     51.74   640.00     73.98%
  62695 requests in 1.00m, 28.58MB read
  Socket errors: connect 0, read 62693, write 0, timeout 0
Requests/sec:   1043.35
Transfer/sec:    487.03KB
```

### 使用HTTPS
想要使用HTTPS，只需要在配置中使用`using_https`即可。
```python
import hibou    # 导入模块
conf = hibou.HttpConfig()
conf.static_path_root("static")   # 设置静态资源的路径
conf.script_path_root("scripts")  # 设置脚本的目录
conf.template_path_root("templates")    # 设置HTML模板文件的目录
# 这里就是设置https的证书，然后
conf.using_https("server.key", "server.crt")
hibou.start_server(conf, "0.0.0.0", 7000)  # 启动HTTP服务
```
关于本地证书：需要安装openssl（注意其中Common Name 一定要设置为对应的IP或者域名
```shell
# 生成私钥
openssl genrsa -out server.key 2048
# 生成证书签名请求 (CSR)
openssl req -new -key server.key -out server.csr
# 生成自签名证书（有效期 1095 天）
openssl x509 -req -days 1095 -in server.csr -signkey server.key -out server.crt
```