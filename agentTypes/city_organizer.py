from icecream import ic
from osbrain import Agent


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

    def shuffle_passenger(self, pos):
        for organizer in self.organizers:
            if pos[0] >= self.organizers[organizer][0][0] and pos[1] >= self.organizers[organizer][0][1]:
                if pos[0] < self.organizers[organizer][1][0] and pos[1] < self.organizers[organizer][1][1]:
                    self.log_info(f"Received request from position {pos} assigned now to {organizer}")
                    return organizer