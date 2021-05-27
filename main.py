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
        edge_index = np.random.randint(0, len(edges), size=1)
        traci.person.add(f"P{i}", edges[edge_index[0]], 0)
        traci.person.appendWaitingStage(f"P{i}", 1000)
        persons.append(f"P{i}")
        #traci.person.subscribe(f"P{i}")

    vehicles = []
    for i in range(0, veh_num):
        edge_index = np.random.randint(0, len(edges), size=2)
        #ic(traci.simulation.findRoute(edges[edge_index[0]], edges[edge_index[1]]))
        #traci.route.add(f'trip-v{i}', [edges[edge_index[0]], edges[edge_index[1]]])
        traci.vehicle.add(f"V{i}", '!veh0', "marshrutka", personCapacity=5,
                          personNumber=0)
        #traci.vehicle.setParkingAreaStop(f"V{i}", "ParkAreaA")
        vehicles.append(f"V{i}")
        traci.vehicle.subscribe(f"V{i}", (traci.tc.VAR_ROAD_ID,
                                          traci.tc.VAR_POSITION, traci.tc.VAR_PERSON_NUMBER))

    organizer.set_attr(passengers=persons, vehicles=vehicles, edges=edges)

    for i in range(0, pass_num):
        edge_index = np.random.randint(0, len(edges), size=1)
        person = run_agent(f"P{i}", base=Passenger, attributes=dict(port=port))
        start_pos = traci.person.getPosition(f"P{i}")
        person.set_attr(index=f"P{i}", target=edges[edge_index[0]], position=start_pos)
        person.connect(addr, alias='organizer', handler=Passenger.read_subscription)
        sleep = random.randint(0, 100)
        ## TODO: figure out a way to make it sleep after the start of the simulation
        person.after(sleep, Passenger.find_me_a_bus)

    for i in range(0, veh_num):
        vehicle = run_agent(f"V{i}", base=MiniBus, attributes=dict(port=port))
        vehicle.set_attr(index=f"V{i}", pass_num=8)
        vehicle.connect(addr, alias='organizer', handler=Passenger.read_subscription)

    organizer.each(1.0, Organizer.check_places)
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        ic(traci.vehicle.getSubscriptionResults('V1'))
        step += 1
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
