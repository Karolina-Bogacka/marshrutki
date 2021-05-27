import random
import time

import traci
from icecream import ic
from osbrain import Agent


class Passenger(Agent):

    def on_init(self):
        ic("on init")

    def read_subscription(self, message):
        self.log_info('Read: "%s"' % message)

    def process_reply(self, message):
        self.log_info('Publisher replied with: "%s"' % message)

    def find_me_a_bus(self):
        self.send('organizer', [self.index, self.target, self.position],
                  handler=Passenger.process_reply)
