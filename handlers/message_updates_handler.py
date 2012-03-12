import logging
import tornado.escape
import tornado.web
from handlers.base_handler import BaseHandler
from mixins.message import MessageMixin


class MessageUpdatesHandler(BaseHandler, MessageMixin):
    def initialize(self, db):
        self.db = db

    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        self.set_header("Access-Control-Allow-Origin","*")
        cursor = self.get_argument("cursor", None)
        room = self.get_argument("room", None)
        logging.info("Requesting update for room %s starting from cursor %s", room, cursor)
        self.wait_for_messages(self.on_new_messages,
            cursor=cursor,
            room=room)

    def options(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', 'GET, PUT, OPTIONS')

    def on_new_messages(self, messages):
        # Closed client connection
        if self.request.connection.stream.closed():
            return
        self.finish(dict(messages=messages))

    def on_connection_close(self):
        user = self.db.users.find_one({"first_name" : self.current_user["first_name"]})
        self.cancel_wait(self.on_new_messages, user["room"])