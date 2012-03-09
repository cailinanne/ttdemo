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
import re

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):

        logging.info("INITIALIZING")
        conn = pymongo.Connection()
        db = conn.simpletest

        handlers = [
            (r"/", MainHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
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


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)


class MainHandler(BaseHandler):
    @tornado.web.authenticated

    # Deliver the initial HTML payload
    # Note that this HTML payload includes the N most recent
    # messages (where N = MessageMixin.cache_size)
    def get(self):
        self.render("index.html", messages=MessageMixin.cache)


class MessageMixin(object):
    waiters = set()
    cache = []
    cache_size = 200

    def wait_for_messages(self, callback, cursor=None):
        cls = MessageMixin
        # The cursor is just the UUID of the latest message that the client has
        # received since the initial HTML payload.  On first request cursor = None
        #
        # If the client is already behind we immediately trigger the new_messages
        # callback. This should only really happen if a new message comes in during
        # the time between the request of the initial HTML payload and the first
        # AJAX triggered request to /a/messages/update
        if cursor:
            index = 0
            for i in xrange(len(cls.cache)):
                index = len(cls.cache) - i - 1
                if cls.cache[index]["id"] == cursor: break
            recent = cls.cache[index + 1:]
            if recent:
                callback(recent)
                return

        # Add the requesting client to the list of waiters (or "observers")
        # Specifically, what we're adding is a function pointer (is that the right word?)
        # to the on_new_messages method
        cls.waiters.add(callback)

    def cancel_wait(self, callback):
        cls = MessageMixin
        cls.waiters.remove(callback)

    def new_messages(self, messages):
        cls = MessageMixin
        logging.info("Sending new message to %r listeners", len(cls.waiters))

        for callback in cls.waiters:
            try:
                # Call on_new_messages, which will finally complete the request
                callback(messages)
            except:
                logging.error("Error in waiter callback", exc_info=True)

        # Empty the list of observers.  Any clients that are still interested
        # will re-register their interest by immediately executing a new
        # POST /a/messages/updates as soon as they get a response from the server
        # See Long Polling: http://en.wikipedia.org/wiki/Push_technology
        cls.waiters = set()

        cls.cache.extend(messages)

        # If the cache of messages has grown bigger then cache_size, trim it
        # and keep only the most recent cache_size messages
        if len(cls.cache) > self.cache_size:
            cls.cache = cls.cache[-self.cache_size:]


class MessageNewHandler(BaseHandler, MessageMixin):
    def initialize(self, db):
        self.db = db


    @tornado.web.authenticated
    # Note that this method is synchronous
    def post(self):
        message = {
            "id": str(uuid.uuid4()),
            "from": self.current_user["first_name"],
            "body": self.get_argument("body"),
        }
        message["html"] = self.render_string("message.html", message=message)
        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            self.write(message)
        self.new_messages([message])
        self.db.chats.insert(message)
        self.save_play(message)


    def save_play(self, message):
        pattern = re.compile(r"\\song (.*)")
        match = pattern.match(message["body"])

        if match != None:
            play = {
                "id" : message["id"],
                "user" : message["from"],
                "song" : match.groups(1)
            }

            self.db.plays.insert(play)

            logging.info("[INFO] Inserted a play")


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
        self.redirect("/")


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.write("You are now logged out")


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
