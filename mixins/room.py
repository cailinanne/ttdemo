import logging
import re

class RoomMixin(object):

    def enter_room(self, room_name):

        room = self.db.rooms.find_one({"name" : room_name})

        if not self.current_user["first_name"] in room["users"]:
            self.db.rooms.update( { "name" : room["name"] }, { "$push": { "users" : self.current_user["first_name"] } } );

        self.db.users.update({"first_name" : self.current_user["first_name"]},  {"$set": {"room": room["name"]}})

    def leave_current_room(self):

        user = self.db.users.find_one({"first_name" : self.current_user["first_name"]})

        if user != None and user.has_key("room"):
            self.db.rooms.update( { "name" : user["room"] }, { "$pull": { "users" : self.current_user["first_name"] } } );
            self.db.users.update({"first_name" : self.current_user["first_name"]},  {"$set": {"room": None }})