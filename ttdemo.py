#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import tornado.auth
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import os.path
import pymongo
from mixins.room import RoomMixin
from handlers.base_handler import BaseHandler
from handlers.message_new_handler import MessageNewHandler
from handlers.message_updates_handler import MessageUpdatesHandler
from handlers.room_handler import RoomHandler
from settings import MONGO_HOST, MONGO_PORT, COOKIE_DOMAIN


from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):

        logging.info("INITIALIZING")
        conn = pymongo.Connection(host=MONGO_HOST,port=MONGO_PORT)
        db = conn.demo

        handlers = [
            (r"/", MainHandler, dict(db=db)),
            (r"/room/([a-z]+)", RoomHandler, dict(db=db)),
            (r"/auth/login", AuthLoginHandler, dict(db=db)),
            (r"/auth/logout", AuthLogoutHandler, dict(db=db)),
            (r"/a/message/new", MessageNewHandler, dict(db=db)),
            (r"/a/message/updates", MessageUpdatesHandler, dict(db=db)),
        ]
        settings = dict(
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/auth/login",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=False,
            autoescape="xhtml_escape",
        )
        tornado.web.Application.__init__(self, handlers, **settings)



class MainHandler(BaseHandler, RoomMixin):
    def initialize(self, db):
        self.db = db

    @tornado.web.authenticated
    # The lobby
    def get(self):
        logging.info(self.current_user)
        self.leave_current_room()
        self.render("index.html")

class AuthLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    def initialize(self, db):
        self.db = db

    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect(ax_attrs=["name"])

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        self.set_cookie("user", self.create_signed_value("user", tornado.escape.json_encode(user)), domain=COOKIE_DOMAIN)

        if self.db.users.find_one({"first_name" : user["first_name"]}) == None:
            self.db.users.insert(user)

        self.redirect("/")


class AuthLogoutHandler(BaseHandler,RoomMixin):
    def initialize(self, db):
        self.db = db

    def get(self):
        self.leave_current_room()
        self.clear_cookie("user")
        self.write("You are now logged out of ttdemo")


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
