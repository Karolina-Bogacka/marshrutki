from enum import Enum
from icecream import ic
from osbrain import Agent


class PassengerState(Enum):
    NO_REQUESTS = -1  # passenger has no requests for reservation
    PASSIVE = 0  # passenger is waiting for the organizer to reserve taxi for it
    WAITING = 1  # passenger is waiting for the taxi
    DRIVING = 2  # passenger is driving in the taxi


class Passenger(Agent):
    id = "passenger"
    edge = ""
    position1D = 0
    position2D = [0, 0]
    destination = None
    state = PassengerState.PASSIVE
    organizer = "organizer"
    current_reservation = -1

    def after_init(self, index, start, position1D, position2D, destination, organizer):
        self.id = index
        ic(f"Passenger init {self.id}")
        self.state = PassengerState.PASSIVE
        self.start = start
        self.position1D = position1D
        self.destination = destination
        self.organizer = organizer
        self.position2D = position2D
        self.waiting = 0

    def spawn_new_request(self, destination):
        if PassengerState.NO_REQUESTS:
            self.destination = destination
            self.state = PassengerState.PASSIVE
            self.waiting = 0

    def get_state(self):
        return self.state

    def handle_state(self):
        if self.state == PassengerState.PASSIVE:
            if self.destination is not None:
                if self.waiting >= 10:
                    self.log_info("Waiting for more than 10 attempts")
                self.ask_for_reservation()
                self.waiting += 1

    def update_reservation(self, message):
        if self.id in message[1]:
            if self.state == PassengerState.WAITING:
                self.log_info("Passenger apparently picked up")
                self.state = PassengerState.DRIVING  # passenger already picked up
            elif self.state == PassengerState.DRIVING:
                self.state = PassengerState.NO_REQUESTS
                self.log_info("Destination apparently reached")

    def update_dispatched(self, message):
        if self.id in message:
            self.state = PassengerState.WAITING
            self.current_reservation = message[self.id]
            self.log_info(f"Passenger {self.id} waiting for dispatched taxi")

    def update_assigned(self, message):
        if self.id in message:
            self.state = PassengerState.WAITING
            self.log_info(f"Passenger {self.id} assigned to a taxi")

    def set_attr(self, index, start_edge, position):
        self.id = index
        self.edge = start_edge
        self.position = position

    def add_request(self, finish_edge):
        self.destination = finish_edge

    def read_subscription(self, message):
        self.log_info('Read: "%s"' % message)

    def process_reply(self, message):
        if not message[0]:
            self.organizer = message[1]
            self.log_info(f'Organizer changes to {self.organizer}')
        else:
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
