import traci
from icecream import ic
from osbrain import Agent


# TODO: I could also add a street name to edge to make better messages but it's not super important now

class Organizer(Agent):
    id = ""
    borders = []
    drivers = []
    passengers = []
    reservations = []
    taxis = {"PASSIVE": {},
             "TO_DISPATCH": {},
             "DRIVING_FULL": {},
             "DRIVING_NOT_FULL": {}
             }

    passengers = {
        "NO_REQUESTS": {},
        "PASSIVE": {},
        "WAITING": {},
        "DRIVING": {}
    }

    def after_init(self, id, edge_positions):
        ic(f"Organizer init {self.id}")
        self.id = id
        self.edge_positions = edge_positions

    def choose_taxi_to_dispatch(self):
        pass

    def set_borders(self, borders):
        self.borders = borders

    def get_borders(self):
        return self.borders

    def set_drivers(self, drivers):
        self.drivers = drivers

    def get_drivers(self):
        return self.drivers

    def set_passengers(self, passengers):
        self.passengers = passengers

    def get_passengers(self):
        return self.passengers

    def set_reservations(self, reservations):
        self.reservations = reservations

    def get_reservations(self):
        return self.reservations

    def set_address(self, address):
        self.address = address

    def get_address(self):
        return self.address

    def get_id(self):
        return self.id

    def reply_back(self, message):
        return f'Received request from {message[0]} travelling to {message[1]}'
