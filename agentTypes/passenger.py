from osbrain import Agent
from enum import Enum
from icecream import ic


class PassengerState(Enum):
    NO_REQUESTS = -1 # passenger has no requests for reservation
    PASSIVE = 0 # passenger is waiting for the organizer to reserve taxi for it
    WAITING = 1 # passenger is waiting for the taxi
    DRIVING = 2 # passenger is driving in the taxi


class Passenger(Agent):

    # TODO: change the position to be two-dimensional, since that's what we get

    id = "passenger"
    edge = ""
    position1D = 0
    position2D = [0,0]
    destination = None
    state = PassengerState.PASSIVE
    organizer = "organizer"

    def after_init(self, id, start, position1D, position2D, destination, organizer):
        ic(f"Passenger init {self.id}")
        self.id = id
        self.state = PassengerState.PASSIVE
        self.start = start
        self.position1D = position1D
        self.destination = destination
        self.organizer = organizer
        self.position2D = position2D

    def handle_state(self):
        if self.state == PassengerState.PASSIVE:
            if self.destination is not None:
                self.ask_for_reservation()


    def set_attr(self, id, start_edge, position):
        self.id = id
        self.edge = start_edge
        self.position = position

    # I guess I could understand it as done on the organizer side.
    def add_request(self, finish_edge):
        self.destination = finish_edge

    def read_subscription(self, message):
        self.log_info('Read: "%s"' % message)

    def process_reply(self, message):
        self.log_info('Organizer replied with: "%s"' % message)

    def set_position(self, position):
        self.position2D = position

    def get_position(self):
        return self.position2D

    def set_id(self, id):
        self.id = id

    def get_id(self):
        return self.id

    def ask_for_reservation(self):
        self.send(self.organizer, [self.id, self.destination, self.start, self.position1D, self.position2D],
                  handler=Passenger.process_reply)
