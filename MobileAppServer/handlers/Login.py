# -*- coding:utf-8 -*-

import ant


@ant.route("/login")
class LoginHandler(ant.RequestHandler):
    def get(self):
        return self.render("login.html")

    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        remember_me = self.get_argument("remember_me", False)

        if username == "admin" and password == "password":
            if remember_me:
                self.set_cookie("username", username, expires_days=30)
            else:
                self.set_cookie("username", username)
            self.redirect("/")
        else:
            return self.response({})
