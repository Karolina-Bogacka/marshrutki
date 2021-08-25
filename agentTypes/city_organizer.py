from icecream import ic
from osbrain import Agent

from utils import check_boundaries


class CityOrganizer(Agent):

    organizers = {}

    def after_init(self, index):
        ic(f"City Organizer init {index}")
        self.id = index

    def set_address(self, address):
        self.address = address

    def get_address(self):
        return self.address

    def set_organizers(self, organizers):
        self.organizers = organizers

    def shuffle_passenger(self, msg):
        for organizer in self.organizers:
            if check_boundaries(msg[0], self.organizers[organizer]):
                self.log_info(f"Received request from passenger {msg[1]} from {msg[2]} assigned now to {organizer}")
                return organizer