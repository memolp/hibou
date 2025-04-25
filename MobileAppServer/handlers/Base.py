# -*- coding:utf-8 -*-

import ant

class BaseHandler(ant.RequestHandler):
    def check_auth(self):
        """ 检查用户是否登录 """
        if not self.get_cookie("UUID"):
            self.redirect('/login')
            return False
        return True