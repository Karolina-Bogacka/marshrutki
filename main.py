# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import os
import random

import traci
import sys
import argparse
import numpy as np
from osbrain import run_nameserver, run_agent
from sumolib.miscutils import getFreeSocketPort
from icecream import ic

from agentTypes.organizer import Organizer
from agentTypes.passenger import Passenger
from agentTypes.vehicle import MiniBus


def simulate(pass_num, veh_num, org_num=1):
    ns = run_nameserver()
    port = getFreeSocketPort()
    sumoBinary = "sumo-gui"
    # here you should probably be able to provide the path to a custom config
    sumoCmd = [sumoBinary, "-c",
               "/Users/karolinabogacka/PycharmProjects/osBrainSumo/configs/simpleConfig"
               ".sumocfg", "--num-clients", "1"]
    traci.start(sumoCmd, port=port)
    edges = traci.edge.getIDList()
    routes = traci.route.getIDList()
    organizer = run_agent('Organizer', base=Organizer, attributes=dict(port=port))
    addr = organizer.bind('SYNC_PUB', alias='organizer', handler=Organizer.reply_back)

    persons = []
    for i in range(0, pass_num):
        edge_index = np.random.randint(0, len(edges), size=2)
        traci.person.add(f"P{i}", edges[edge_index[0]], 0)
        traci.person.appendWaitingStage(f"P{i}", 1000)
        persons.append(f"P{i}")
        person = run_agent(f"P{i}", base=Passenger, attributes=dict(port=port))
        person.set_attr(index=f"P{i}", target=edges[edge_index[1]])
        person.connect(addr, alias='organizer', handler=Passenger.read_subscription)
        sleep = random.randint(0, 100)
        ## TODO: figure out a way to make it sleep after the start of the simulation
        person.after(sleep, Passenger.find_me_a_bus)

    vehicles = []
    for i in range(0, veh_num):
        route_index = np.random.randint(0, len(routes), size=1).item()
        traci.vehicle.add(f"V{i}", routes[route_index])
        vehicles.append(f"V{i}")
        traci.vehicle.subscribe(f"V{i}")
        vehicle = run_agent(f"V{i}", base=MiniBus, attributes=dict(port=port))
        person.set_attr(index=f"P{i}", target=edges[edge_index[1]])
        person.connect(addr, alias='organizer', handler=Passenger.read_subscription)

    organizer.set_attr(passengers=persons, vehicles=vehicles, edges=edges)
    organizer.each(1.0, Organizer.check_places)
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        pos = traci.vehicle.getIDList()[0]
        step += 1
        if step == 1000:
            traci.close(False)
            ns.shutdown()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('vehicles', type=int,
                        help='number of vehicles for the simulation')
    parser.add_argument('passengers', type=int,
                        help='number of passengers for the simulation')

    # parse the arguments
    args = parser.parse_args()
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("please declare environment variable 'SUMO_HOME'")
    simulate(args.passengers, args.vehicles)
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
