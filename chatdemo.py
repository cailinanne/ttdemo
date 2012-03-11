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
import uuid
import pymongo
from mixins.message import MessageMixin
from mixins.room import RoomMixin
from handlers.message_new_handler import MessageNewHandler
from handlers.base_handler import BaseHandler

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):

        logging.info("INITIALIZING")
        conn = pymongo.Connection()
        db = conn.demo

        handlers = [
            (r"/", MainHandler, dict(db=db)),
            (r"/room/([a-z]+)", RoomHandler, dict(db=db)),
            (r"/auth/login", AuthLoginHandler, dict(db=db)),
            (r"/auth/logout", AuthLogoutHandler, dict(db=db)),
            (r"/a/message/new", MessageNewHandler, dict(db=db)),
            (r"/a/message/updates", MessageUpdatesHandler),
        ]
        settings = dict(
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/auth/login",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            autoescape="xhtml_escape",
        )
        tornado.web.Application.__init__(self, handlers, **settings)



class MainHandler(BaseHandler, RoomMixin):
    def initialize(self, db):
        self.db = db


    @tornado.web.authenticated
    # Deliver the initial HTML payload
    # Note that this HTML payload includes the N most recent
    # messages (where N = MessageMixin.cache_size)
    def get(self):
        logging.info(self.current_user)
        self.leave_current_room()
        self.render("index.html")

class RoomHandler(BaseHandler, RoomMixin):
    def initialize(self, db):
        self.db = db

    @tornado.web.authenticated
    # Deliver the initial HTML payload
    # Note that this HTML payload includes the N most recent
    # messages (where N = MessageMixin.cache_size)
    def get(self, room_name):
        logging.info(self.current_user)
        self.enter_room(room_name)
        room = self.db.rooms.find_one({"name" : room_name})
        self.render("room.html", messages=MessageMixin.cache, room=room)


class MessageUpdatesHandler(BaseHandler, MessageMixin):
    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        cursor = self.get_argument("cursor", None)
        logging.info("Requesting update starting from cursor %s", cursor)
        self.wait_for_messages(self.on_new_messages,
                               cursor=cursor)

    def on_new_messages(self, messages):
        # Closed client connection
        if self.request.connection.stream.closed():
            return
        self.finish(dict(messages=messages))

    def on_connection_close(self):
        self.cancel_wait(self.on_new_messages)


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

        self.set_secure_cookie("user", tornado.escape.json_encode(user))

        if self.db.users.find_one({"first_name" : user["first_name"]}) == None:
            self.db.users.insert(user)

        self.redirect("/")


class AuthLogoutHandler(BaseHandler,RoomMixin):
    def initialize(self, db):
        self.db = db

    def get(self):
        self.leave_current_room()
        self.clear_cookie("user")
        self.write("You are now logged out")


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
