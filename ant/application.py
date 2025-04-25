# -*- coding:utf-8 -*-

from .http import HttpServer


class Application:
    # 单例对象
    _instance = None

    @staticmethod
    def ins():
        if Application._instance is None:
            Application._instance = Application()
        return Application._instance

    def __init__(self):
        super().__init__()
        self.logger = None
        self.logger_level = logging.INFO
        self.namespace = {}
        self.static_path = None
        self.upload_path = None
        self.script_path = None
        self.template_path = None
        self.routes = {}

    def bind_runtime(self, name, runtime):
        if not isinstance(runtime, AntRuntime):
            raise ValueError("runtime must be an instance of AntRuntime")
        self.namespace[name] = runtime

    def static_path_root(self, path):
        self.static_path = path

    def upload_path_root(self, path):
        self.upload_path = path

    def script_path_root(self, path):
        self.script_path = path

    def template_path_root(self, path):
        self.template_path = path

    def set_logger(self, logger):
        self.logger = logger

    def set_logger_level(self, level):
        self.logger_level = level

    def start_server(self, host="127.0.0.1", port=8080):
        if self.logger is None:
            self.logger = logging.getLogger("Application")
        self.logger.setLevel(self.logger_level)
        # if self.static_path is not None:
            # self.routes["/static"] =
        server = HttpServer(self, host, port)
        server.start()

