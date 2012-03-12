import logging
import uuid
import tornado.escape
import tornado.web
from handlers.base_handler import BaseHandler
from mixins.message import MessageMixin
from settings import ORIGIN_SERVER

class MessageNewHandler(BaseHandler, MessageMixin):
    def initialize(self, db):
        self.db = db
        self.set_header('Access-Control-Allow-Origin', ORIGIN_SERVER)
        self.set_header('Access-Control-Allow-Credentials', 'true')


    @tornado.web.authenticated
    # Note that this method is synchronous
    def post(self):
        message = {
            "id": str(uuid.uuid4()),
            "from": self.current_user["first_name"],
            "body": self.get_argument("body"),
            "room": self.get_argument("room")
            }

        #message["html"] = self.render_string("message.html", message=message)

        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            self.write(message)

        self.new_messages([message], self.get_argument("room"))
        self.save_message(message)
        self.save_play(message)


    def options(self):
        self.set_header('Access-Control-Allow-Methods', 'GET, PUT, OPTIONS')
        self.set_header('Access-Control-Allow-Headers', 'X-Requested-With')