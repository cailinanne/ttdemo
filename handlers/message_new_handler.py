import logging
import uuid
import tornado.escape
import tornado.web
from handlers.base_handler import BaseHandler
from mixins.message import MessageMixin

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

        #message["html"] = self.render_string("message.html", message=message)

        if self.get_argument("next", None):
            self.redirect(self.get_argument("next"))
        else:
            self.write(message)

        self.new_messages([message])
        self.save_message(message)
        self.save_play(message)