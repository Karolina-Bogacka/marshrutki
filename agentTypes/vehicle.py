import traci
from enum import Enum
from icecream import ic
from osbrain import Agent


class MiniBusState(Enum):
    PASSIVE = 0,
    TO_DISPATCH = 1,
    DRIVING_FULL = 2,
    DRIVING_NOT_FULL = 3


class MiniBus(Agent):

    id = "vehicle"
    edge = ""
    position = 0
    destination = ""
    state = MiniBusState.PASSIVE
    available_places = 8
    free_places = 8

    def after_init(self, id, available_places=8, free_places=8):
        ic(f"Marshrutka init {self.id}")
        self.id = id
        self.state = MiniBusState.PASSIVE

    def set_position(self, position):
        self.position = position

    def get_position(self):
        return self.position

    def handle_state(self):
        ic(f"Handling state {self.id}")

    def read_subscription(self, message):
        self.log_info('Read: "%s"' % message)

    def process_reply(self, message):
        self.log_info('Publisher replied with: "%s"' % message)
