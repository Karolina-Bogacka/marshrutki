import traci
from enum import Enum
from icecream import ic
from osbrain import Agent


class MiniBusState(Enum):
    PASSIVE = 0
    WAITING = 1
    DRIVING = 2


class MiniBus(Agent):

    def on_init(self, available_places=8, free_places=8):
        ic("on init minibus")

    def read_subscription(self, message):
        self.log_info('Read: "%s"' % message)

    def process_reply(self, message):
        self.log_info('Publisher replied with: "%s"' % message)
