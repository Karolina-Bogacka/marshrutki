import random
import time

import traci
from icecream import ic
from osbrain import Agent
from enum import Enum
import numpy as np


class PassengerState(Enum):
    PASSIVE = 0
    WAITING = 1
    DRIVING = 2


class Passenger(Agent):

    def on_init(self):
        self.state = PassengerState.PASSIVE

    def set_attr(self, id, start_edge, position):
        self.id = id
        self.edge = start_edge
        self.position = position

    # I guess I could understand it as done on the organizer side.
    def add_request(self, finish_edge):
        self.destination = finish_edge
        self.state = PassengerState.WAITING

    def read_subscription(self, message):
        self.log_info('Read: "%s"' % message)

    def process_reply(self, message):
        self.log_info('Publisher replied with: "%s"' % message)

    def find_me_a_bus(self):
        self.send('organizer', [self.index, self.target, self.position],
                  handler=Passenger.process_reply)
