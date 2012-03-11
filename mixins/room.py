import logging
import re

class RoomMixin(object):

    def enter_room(self):

        if self.db.users.find_one({"first_name" : self.current_user["first_name"]}) == None:
            self.db.users.insert(self.current_user)

        # TODO: Let users enter different rooms
        room = self.db.rooms.find_one({"name" : "demoroom"})

        if not self.current_user["first_name"] in room["users"]:
            self.db.rooms.update( { "name" : "demoroom" }, { "$push": { "users" : self.current_user["first_name"] } } );

        self.db.users.update({"first_name" : self.current_user["first_name"]},  {"$set": {"room": room["name"]}})