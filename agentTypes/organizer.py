import traci
from icecream import ic
from osbrain import Agent


class Organizer(Agent):

    def on_init(self):
        ic("on init")

    # periodically check the situation, probably
    def check_places(self):
        print("*****************")
        #for v in self.vehicles:
        #    print(traci.vehicle.getSubscriptionResults(v))

    def reply_back(self, message):
        positions = [traci.vehicle.getSubscriptionResults(v) for v in self.vehicles]
        return 'Received %s' % message[0]
