import traci
from icecream import ic
from osbrain import Agent


class Organizer(Agent):

    def on_init(self):
        ic("on init")

    def connect_traci(self):
        self.connection = traci.connect(port=self.port, numRetries=10)
        self.connection.setOrder(2)

    def step_simulation(self):
        traci.simulationStep()

        # periodically check the situation, probably
    def check_places(self):
        print("*****************")
        ic(traci.vehicle.getIDList())
        #for v in range(0, len(self.vehicles)):
            #ic(traci.vehicle.getSubscriptionResults(self.vehicles[v]))

    def reply_back(self, message):
        ic(self.vehicles)
        positions = [traci.vehicle.getSubscriptionResults(v) for v in self.vehicles]
        #ic(positions)
        return 'Received %s' % str(message[2])
