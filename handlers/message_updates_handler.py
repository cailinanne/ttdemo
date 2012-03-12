import logging
import tornado.escape
import tornado.web
from handlers.base_handler import BaseHandler
from mixins.message import MessageMixin
from settings import ORIGIN_SERVER


class MessageUpdatesHandler(BaseHandler, MessageMixin):
    def initialize(self, db):
        logging.info("[INFO] Initializing MessageUpdatesHandler")
        self.db = db
        self.set_header('Access-Control-Allow-Origin', ORIGIN_SERVER)
        self.set_header('Access-Control-Allow-Credentials', 'true')

    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        cursor = self.get_argument("cursor", None)
        room = self.get_argument("room", None)
        logging.info("Requesting update for room %s starting from cursor %s", room, cursor)
        self.wait_for_messages(self.on_new_messages,
            cursor=cursor,
            room=room)

    def options(self):
        self.set_header('Access-Control-Allow-Methods', 'GET, PUT, POST, OPTIONS')
        self.set_header('Access-Control-Allow-Headers', 'X-Requested-With')

    def on_new_messages(self, messages):
        # Closed client connection
        if self.request.connection.stream.closed():
            return
        self.finish(dict(messages=messages))

    def on_connection_close(self):
        user = self.db.users.find_one({"first_name" : self.current_user["first_name"]})
        self.cancel_wait(self.on_new_messages, user["room"])