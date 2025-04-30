# hibou
一个简单的Python语言写的Http服务器，可以理解他是一个玩具，代码简单方便快速使用。
我主要用它可以搭建一些团队内部使用的平台工具。


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
./wrk -c 100 -t 2 -d 60 http://172.25.22.37:7000/
Running 1m test @ http://172.25.22.37:7000/
  2 threads and 100 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    94.88ms    6.92ms 152.02ms   88.34%
    Req/Sec   524.64     51.74   640.00     73.98%
  62695 requests in 1.00m, 28.58MB read
  Socket errors: connect 0, read 62693, write 0, timeout 0
Requests/sec:   1043.35
Transfer/sec:    487.03KB
```