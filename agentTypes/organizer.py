import traci
from icecream import ic
from osbrain import Agent


class Organizer(Agent):

    borders = []
    drivers = []
    passengers = []
    reservations = []


    def on_init(self):
        ic("on init")

    def connect_traci(self):
        connection = traci.connect(port=self.port, numRetries=10)
        connection.setOrder(2)

    def step_simulation(self):
        traci.simulationStep()

    def check_places(self):
        print("*****************")
        ic(traci.vehicle.getIDList())
        #for v in range(0, len(self.vehicles)):
            #ic(traci.vehicle.getSubscriptionResults(self.vehicles[v]))

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

    def reply_back(self, message):
        ic(self.vehicles)
        positions = [traci.vehicle.getSubscriptionResults(v) for v in self.vehicles]
        #ic(positions)
        return 'Received %s' % str(message[2])
