import logging
import re

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