# -*- coding:utf-8 -*-

import hibou
import Base


@hibou.route(r"/")
class IndexHandler(Base.BaseHandler):
    def get(self):
        if not self.check_auth():
            self.redirect("/login")
            return
        self.write("Hello, world")


