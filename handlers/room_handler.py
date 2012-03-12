import logging
import tornado.escape
import tornado.web
from handlers.base_handler import BaseHandler
from mixins.room import RoomMixin
from mixins.message import MessageMixin

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
        chat_server = self.get_chat_server(room_name)
        self.render("room.html", messages=MessageMixin.caches[room_name].cache, room=room, chat_server=chat_server)

