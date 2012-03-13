import logging
import tornado.escape
import tornado.web
import uuid
from handlers.base_handler import BaseHandler
from mixins.room import RoomMixin
from mixins.message import MessageMixin

class RoomHandler(BaseHandler, RoomMixin, MessageMixin):
    def initialize(self, db):
        self.db = db

    @tornado.web.authenticated
    # Deliver the initial HTML payload
    # Note that this HTML payload includes the 3 most recent messages
    def get(self, room_name):
        self.enter_room(room_name)

        message = {
            "id": str(uuid.uuid4()),
            "from": self.current_user["first_name"],
            "body": "\enter",
            "room": room_name
        }
        self.new_messages([message], room_name)

        room = self.db.rooms.find_one({"name" : room_name})

        # Goofy.  Can't figure out how to reverse the order of the most recent three without
        # stuffing these results in a list (instead of a cursor)
        messages = []
        for message in self.db.messages.find({"room" : room_name}).sort("$natural",-1).limit(3):
            messages.append(message)

        messages.reverse()

        chat_server = self.get_chat_server(room_name)
        self.render("room.html", messages=messages, room=room, chat_server=chat_server)

