from collections import Counter

from enum import Enum
from icecream import ic
from osbrain import Agent


class MiniBusState(Enum):
    TO_DISPATCH = -1,
    PASSIVE = 0,
    DRIVING_FULL = 1,
    DRIVING_NOT_FULL = 2


class MiniBus(Agent):
    id = "vehicle"
    edge = ""
    position2D = [0, 0]
    destination = ""
    state = MiniBusState.PASSIVE
    available_places = 8
    free_places = 8
    organizer = "organizer"
    passengers = []
    stops = {}
    reservations = {}
    order = []

    def after_init(self, id, organizer, available_places=8, free_places=8):
        ic(f"Marshrutka init {self.id}")
        self.id = id
        self.state = MiniBusState.PASSIVE
        self.organizer = organizer
        self.available_places = available_places
        self.free_places = free_places

    def set_position(self, position):
        self.position2D = position

    def get_position(self):
        return self.position2D

    def handle_state(self):
        ic(f"Handling state {self.id}")
        self.send(self.organizer, [self.id, self.position2D], handler=MiniBus.process_reply)
        if self.available_places == 0 and self.state != MiniBusState.DRIVING_FULL:
            self.state = MiniBusState.DRIVING_FULL

    def read_subscription(self, message):
        if self.id == message[0]:
            if self.state == MiniBusState.PASSIVE or self.state == MiniBusState.DRIVING_NOT_FULL or self.state == MiniBusState.TO_DISPATCH:
                self.state = MiniBusState.TO_DISPATCH
                self.passengers.append(message[1])
                self.stops[message[1]] = message[2]
                self.order = message[3]
                self.log_info(f'Read and approved request from {message[1]} to reach {message[2]}')
                return True

    def update_picked(self, picked):
        for p in picked:
            if p in self.order and self.order.count(p) == 2:
                self.order.remove(p)
                self.log_info(f"Picked up passenger {p}")
                self.send(self.organizer, ["Picked up", p, self.id, self.order], handler=MiniBus.process_reply)
                # but it doesn't make sense to remove it from reservations just yet

    def update_delivered(self, picked):
        counted_orders = Counter(self.order)
        for c in counted_orders:
            if counted_orders[c] == 1 and c not in picked:
                self.order.remove(c)
                del self.reservations[c]
                self.update_free_places(change=1)
                self.log_info(f"Delivered passenger {c}")
                self.send(self.organizer, ["Delivered", c, self.id, self.order], handler=MiniBus.process_reply)

    def process_reply(self, message):
        self.log_info('Publisher replied with: "%s"' % message)

    def get_newest_passenger(self):
        return self.passengers[-1]

    def get_passengers(self):
        return self.passengers

    def get_order(self):
        return self.order

    def get_reservations(self):
        return self.reservations

    def set_reservation(self, passenger, res):
        self.reservations[passenger] = res

    def get_stops(self):
        return self.stops

    def get_stop(self, passenger):
        ic(self.stops)
        return self.stops[passenger]

    def update_dispatched(self, passengers):
        self.update_free_places(-len(passengers))
        for passenger in passengers:
            self.send(self.organizer, ["Dispatched", self.id, passenger, self.stops[passenger], self.state, self.reservations[passenger]], handler=MiniBus.handle_dispatched_confirmation)

    def handle_dispatched_confirmation(self, message):
        ic("Handle dispatched")
        self.log_info("Dispatch confirmed")

    def update_free_places(self, change=-1):
        # how should I update free places when a customer leaves?
        # I think I will have to go back here after I implement passengers leaving communication
        self.free_places += change
        if self.free_places <= 0:
            self.state = MiniBusState.DRIVING_FULL
        elif self.free_places >=8:
            self.state = MiniBusState.PASSIVE
        elif self.free_places > 0:
            self.state = MiniBusState.DRIVING_NOT_FULL

    def get_free_places(self):
        return self.free_places

    def check_to_dispatch(self):
        return self.state == MiniBusState.TO_DISPATCH
