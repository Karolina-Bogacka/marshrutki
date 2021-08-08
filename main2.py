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


def gen_route(edges):
    try:
        from_edge = np.random.randint(len(edges))
        to_edge = np.random.randint(len(edges))
        route_stage = traci.simulation.findRoute(edges[from_edge],
                                                 edges[to_edge], vType='marshrutka')
        # check if route valid and long enough to be sensible
        if not route_stage.edges:
            raise Exception("Bad Route")
        ic(route_stage)
        return route_stage
    except:
        return gen_route(edges)


def generateRoutes(num_routes):
    routes = []
    for i in range(num_routes):
        # set route id
        route_id = f"route_{i}"
        # set route endpoints
        edges = traci.edge.getIDList()
        route_stage = gen_route(edges)
        # add route
        if route_stage:
            routes.append((route_id, route_stage))
            traci.route.add(route_id, route_stage.edges)
    return routes

def readAndAssignRoutes(num_routes):
    pass


def simulate(pass_num, veh_num, org_num=1):
    ns = run_nameserver()
    port = getFreeSocketPort()
    ic(port)
    sumoBinary = "sumo-gui"
    # here you should probably be able to provide the path to a custom config
    # sumoCmd = [sumoBinary, "-c",
    #           r"configs\simpleConfig.sumocfg", "--num-clients", "1"]
    num_clients = pass_num + veh_num + org_num + 1
    sumoCmd = [sumoBinary, "-c",
               r"config-smaller-berlin/osm.sumocfg", "--num-clients", "1", "--device.taxi.dispatch-algorithm", "traci",
               "--device.taxi.idle-algorithm", "randomCircling", "--device.rerouting.explicit", "marshrutka"]

    traci.start(sumoCmd, port=port)
    # traci.setOrder(1)

    organizer = run_agent('Organizer', base=Organizer, attributes=dict(port=port))
    addr = organizer.bind('SYNC_PUB', alias='organizer', handler=Organizer.reply_back)
    # organizer.connect_traci()

    # organizer.each(1.0, organizer.step_simulation)
    # organizer.check_places()
    edges = traci.edge.getIDList()
    routes = traci.route.getIDList()
    ic(routes)
    ic(traci.route.getEdges('!0'))

    routes_generated = generateRoutes(20)

    lanes = traci.lane.getIDList()
    edges = {}
    for lane in traci.lane.getIDList():
        edge = traci.lane.getEdgeID(lane)
        if edge not in edges:
            edges[edge] = lane

    # air distance, for isDriving get driving distance
    edge_dict = {}

    for lane in traci.lane.getIDList():
        edge = traci.lane.getEdgeID(lane)
        start = traci.simulation.convert2D(traci.lane.getEdgeID(lanes[0]), 0)
        end = traci.simulation.convert2D(traci.lane.getEdgeID(lanes[0]), traci.lane.getLength(lanes[0]))

        if edge not in edge_dict:
            edge_dict[edge] = (0, traci.lane.getLength(lanes[0]))

    vehicles = []
    for i in range(veh_num):
        traci.vehicle.add(f"vehicle-{i}", routes_generated.pop()[0], "marshrutka", departPos="random", line="taxi")

    passengers = []
    for i in range(pass_num):
        random_route = routes_generated.pop()
        person = run_agent(f"P{i}", base=Passenger, attributes=dict(port=port))
        lanes = traci.lane.getIDList()
        current_lane = [lane for lane in lanes if random_route[1].edges[0] in lane].pop()
        ic(traci.lane.getLength(current_lane))
        lane_length = traci.lane.getLength(current_lane)
        position = np.random.randint(int(lane_length)) if lane_length > 1 else 0
        person.set_attr(id=f"passenger-{i}", start_edge=random_route[1].edges[0], position=position)
        person.on_init()
        traci.person.add(f"passenger-{i}", random_route[1].edges[0], position)
        traci.person.subscribe(f"passenger-{i}", ["66"])
        person.connect(addr, alias='organizer', handler=Passenger.read_subscription)
        traci.person.appendDrivingStage(f"passenger-{i}", random_route[1].edges[-1], 'taxi')
        person.add_request(random_route[1].edges[-1])
        passengers.append(person)

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        reservations = traci.person.getTaxiReservations()
        ic(reservations)
        ic(traci.vehicle.getTaxiFleet(1))
        for i in range(len(reservations)):
            if reservations[i].state == 1:
                ic(reservations[i].fromEdge)
                ic(reservations[i].toEdge)
                ic(traci.vehicle.getRoute(f'vehicle-{i}'))
                ic(traci.simulation.findRoute(traci.vehicle.getRoute(f'vehicle-{i}')[0],
                                           reservations[i].fromEdge, vType='marshrutka'))
                traci.vehicle.dispatchTaxi(f'vehicle-{i}', [reservations[i].id])
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
