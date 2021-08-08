import traci
from icecream import ic
from osbrain import Agent


class MiniBus(Agent):

    def on_init(self, available_places=8, free_places=8):
        ic("on init minibus")

    def connect_traci(self):
        self.connection = traci.connect(port=self.port, numRetries=10, host="localhost")

    def step_simulation(self):
        traci.simulationStep()

    def read_subscription(self, message):
        self.log_info('Read: "%s"' % message)

    def process_reply(self, message):
        self.log_info('Publisher replied with: "%s"' % message)
