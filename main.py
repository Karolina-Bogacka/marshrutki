# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import os

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

'''
Notes:
- I can define bus stops in the map and drive between them for the later experiment
- 
'''

def greedyRecursive(built, end, edges):
    if built[-1] == end[0]:
        return built
    else:
        ic(built)
        links = [l for l in traci.lane.getLinks(edges[built[-1]]) if traci.lane.getEdgeID(l[0]) not in built]
        ic(links)
        min_edge = None
        min_dist = -1
        results = None
        min_l = ""
        while not results:
            if min_l in links:
                links.remove(min_l)
            ic(links)
            if not links:
                return None
            for l in links:
                if l[0] == end[0]:
                    min_edge = end[0]
                    break
                len = traci.lane.getLength(l[0])
                edge = traci.lane.getEdgeID(l[0])
                dist = traci.simulation.getDistanceRoad(edge, len / 2, end[0], end[1])
                if min_dist < 0:
                    min_dist = dist
                    min_edge = edge
                    min_l = l
                elif min_dist > dist:
                    min_dist = dist
                    min_edge = edge
                    min_l = l
            built.append(min_edge)
            results = greedyRecursive(built, end, edges)
        return results

def greedyRouteBuilder(position, end, edges):
    # naiive, very much non optimized version
    # I can also just choose a random position at the end, I guess
    built = [position[0]]
    return greedyRecursive(built,end, edges)



def simulate(pass_num, veh_num, org_num=1):
    ns = run_nameserver()
    port = getFreeSocketPort()
    sumoBinary = "sumo-gui"
    # here you should probably be able to provide the path to a custom config
    # sumoCmd = [sumoBinary, "-c",
    #           r"C:\Users\kboga\PycharmProjects\marshrutki\configs\simpleConfig.sumocfg", "--num-clients", "1"]
    sumoCmd = [sumoBinary, "-c",
               r"C:\Users\kboga\PycharmProjects\marshrutki\simpleConfigPoraj.sumocfg", "--num-clients", "1"]
    traci.start(sumoCmd, port=port)
    edges = traci.edge.getIDList()
    routes = traci.route.getIDList()
    ic(routes)
    organizer = run_agent('Organizer', base=Organizer, attributes=dict(port=port))
    addr = organizer.bind('SYNC_PUB', alias='organizer', handler=Organizer.reply_back)

    start = '252291164#3'
    finale = '364695971'
    ic(traci.simulation.findRoute(start, finale, vType='marshrutka'))
    route = traci.simulation.findRoute(start, finale, vType='marshrutka')
    traci.route.add(f'new', route.edges)
    traci.vehicle.add(f"trial", f'new', "marshrutka", personCapacity=5,
                      personNumber=0)

    lanes = traci.lane.getIDList()
    edges = {}
    for lane in traci.lane.getIDList():
        edge = traci.lane.getEdgeID(lane)
        if edge not in edges:
            edges[edge] = lane

    greedy_edges = greedyRouteBuilder([start, 0], [finale, 0], edges)
    traci.route.add(f'new2', greedy_edges)
    traci.vehicle.add(f"trial", f'new2', "marshrutka", personCapacity=5,
                      personNumber=0)

    # air distance, for isDriving get driving distance
    edge_dict = {}
    # ic(traci.lane.getIDList())
    # ic(traci.lane.getEdgeID(lanes[0]))
    # ic(traci.lane.getLength(lanes[0]))
    # ic(traci.simulation.convert2D(traci.lane.getEdgeID(lanes[0]), 0))
    # ic(traci.simulation.convert2D(traci.lane.getEdgeID(lanes[0]), traci.lane.getLength(lanes[0])))

    # I wonder if the beginning position of the next edge is the ending of this one
    # welp, nevermind. better start the dictionary - graph - thing, just - how?
    # build based on lanes, but save based on edges. we need to have edges and lengths of edges, and then we can build a distance graph
    # djikstra
    for lane in traci.lane.getIDList():
        edge = traci.lane.getEdgeID(lane)
        start = traci.simulation.convert2D(traci.lane.getEdgeID(lanes[0]), 0)
        end = traci.simulation.convert2D(traci.lane.getEdgeID(lanes[0]), traci.lane.getLength(lanes[0]))

        if edge not in edge_dict:
            edge_dict[edge] = (0,  traci.lane.getLength(lanes[0]))

    ic(traci.simulation.getDistanceRoad(edges[0], 0, edges[1], 0))
    '''
    persons = []
    for i in range(0, pass_num):
        edge_index = np.random.randint(0, len(edges), size=1)
        traci.person.add(f"P{i}", edges[edge_index[0]], 0)
        traci.person.appendWaitingStage(f"P{i}", 100)
        ic(traci.person.getTaxiReservations())
        persons.append(f"P{i}")
        #traci.person.subscribe(f"P{i}")

    vehicles = []
    routes = traci.route.getIDList()
    ic(routes)
    for i in range(0, veh_num):
        edge_index = np.random.randint(0, len(edges), size=2)
        while (abs(edge_index[1] - edge_index[0]) < 5):
            edge_index = np.random.randint(0, len(edges), size=2)
        ic(traci.simulation.findRoute(edges[edge_index[0]], edges[edge_index[1]],  vType='marshrutka'))
        traci.route.add(f'trip-v{i}', [edges[edge_index[0]], edges[edge_index[1]]])
        traci.vehicle.add(f"V{i}", f'trip-v{i}', "marshrutka", personCapacity=5,
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
        #sleep = random.randint(0, 100)
        ## TODO: figure out a way to make it sleep until after the start of the simulation
        #person.after(sleep, Passenger.find_me_a_bus)
        traci.person.appendDrivingStage(f"P{i}", edges[edge_index[0]], "taxi")

    for i in range(0, veh_num):
        vehicle = run_agent(f"V{i}", base=MiniBus, attributes=dict(port=port))
        vehicle.set_attr(index=f"V{i}", pass_num=8)
        vehicle.connect(addr, alias='organizer', handler=Passenger.read_subscription)

    ic(traci.route.getIDList())
    organizer.each(1.0, Organizer.check_places)'''
    step = 0
    begin_edge = start
    begin_pos = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        ic(traci.vehicle.getLanePosition("trial"))
        ic(traci.lane.getEdgeID(traci.vehicle.getLaneID("trial")))
        links = traci.lane.getLinks(traci.vehicle.getLaneID("trial"))
        for link in links:
            ic(traci.lane.getEdgeID(link[0]))
        if traci.lane.getEdgeID(traci.vehicle.getLaneID("trial")) != begin_edge:
            begin_edge = traci.lane.getEdgeID(traci.vehicle.getLaneID("trial"))
            begin_pos = traci.vehicle.getLanePosition("trial")
        position = traci.vehicle.getLanePosition("trial")
        ic(abs(position-begin_pos))
        ic(edge_dict[traci.lane.getEdgeID(traci.vehicle.getLaneID("trial"))][1])
        if edge_dict[traci.lane.getEdgeID(traci.vehicle.getLaneID("trial"))][1]<abs(position-begin_pos)+10:
            # time to greedily reroute, I guess
            ic("in greedy")
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
