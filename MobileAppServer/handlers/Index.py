# -*- coding:utf-8 -*-

import ant
import Base


@ant.route(r"/")
class IndexHandler(Base.BaseHandler):
    def get(self):
        if not self.check_auth():
            self.redirect("/login")
            return

        self.get_cookie("UUID")
        self.write("Hello, world")


