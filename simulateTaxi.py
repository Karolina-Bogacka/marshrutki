import math
import os

import osbrain
import traci
import sys
import argparse

from defusedxml import minidom
import random
from osbrain import run_nameserver, run_agent
from sumolib.miscutils import getFreeSocketPort
from icecream import ic
from agentTypes.organizer import Organizer
from agentTypes.passenger import Passenger
from utils import closest_divisors


def assign_organizer(edge, position, subject, organizers):
    pos = traci.simulation.convert2D(edge, position)
    for org in organizers:
        borders = org.get_borders()
        if pos[0] >= borders[0][0] and pos[1] >= borders[0][1]:
            if pos[0] < borders[1][0] and pos[1] < borders[1][1]:
                passes = org.get_passengers()
                passes.append(subject)
                org.set_passengers(passes)
                return True
    return False



def simulation_setup(pass_num, veh_num, org_num, port, generated_routes):
    divisors = closest_divisors(org_num)
    boundaries = traci.simulation.getNetBoundary()[1]
    difference = [int(boundaries[0] / divisors[0]), int(boundaries[1] / divisors[1])]

    start_end = [0, 0]
    new_end = [difference[0], difference[1]]
    generated = read_generated_routes(generated_routes)
    lanes = traci.lane.getIDList()
    lengths = {traci.lane.getEdgeID(lane): traci.lane.getLength(lane) for lane in lanes}

    organizers = []
    indexes = divisors.copy()
    for o in range(org_num):
        organizer = run_agent(f'organizer-{o}', base=Organizer, attributes=dict(port=port))
        organizer.set_borders([start_end, new_end])
        addr = organizer.bind('SYNC_PUB', alias=f'organizer-{o}', handler=Organizer.reply_back)
        organizers.append(organizer)
        if indexes[1] == 1:
            start_end[0] = new_end[0]
            new_end[0] += difference[0]
            indexes[1] = divisors[1]
            start_end[1] = 0
            new_end[1] = difference[1]
        else:
            start_end[1] = new_end[1]
            new_end[1] += difference[1]
            indexes[1] -= 1

    passengers = []
    for i in range(pass_num):
        route = traci.route.getEdges(generated[-1 * i])
        position = random.randrange(0, math.floor(lengths[route[0]]))
        traci.person.add(f'person-{i}', route[0], position)
        traci.person.appendDrivingStage(f"person-{i}", route[-1], 'taxi')
        passenger = run_agent(f'person-{i}', base=Passenger)
        assign_organizer(route[0], position, passenger, organizers)

    vehicles = []
    for i in range(veh_num):
        traci.vehicle.add(f'vehicle-{i}', generated[i], typeID="marshrutka", line="taxi")

    return organizers, passengers, vehicles


def read_generated_routes(file):
    ids = []
    xmldoc = minidom.parse(file)
    itemlist = xmldoc.getElementsByTagName('trip')
    trips = [[item.attributes['from'].value, item.attributes['to'].value] for item in itemlist]
    routes = [traci.simulation.findRoute(trip[0], trip[1], vType="marshrutka") for trip in trips]
    for i in range(len(routes)):
        id_route = f'route-taxi-{i}'
        traci.route.add(id_route, routes[i].edges)
        ids.append(id_route)
    return ids


def simulate(pass_num, veh_num, org_num=1, generated_routes='config-smaller-berlin/output-trips.xml'):
    ns = run_nameserver()
    port = getFreeSocketPort()
    sumoBinary = "sumo-gui"
    sumoCmd = [sumoBinary, "-c",
               r"config-smaller-berlin/osm.sumocfg", "--num-clients", "1", "--device.taxi.dispatch-algorithm", "traci",
               "--device.taxi.idle-algorithm", "randomCircling", "--device.rerouting.explicit", "marshrutka"]
    traci.start(sumoCmd, port=port)

    organizers, passengers, vehicles = simulation_setup(pass_num, veh_num, org_num, port, generated_routes)

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        reservations = traci.person.getTaxiReservations()
        for i in range(len(reservations)):
            if reservations[i].state == 1:
                traci.vehicle.dispatchTaxi(f'vehicle-{i}', [reservations[i].id])
        step += 1
    traci.close(False)
    ns.shutdown()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    osbrain.config['SERIALIZER'] = 'raw'

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
    simulate(args.passengers, args.vehicles, 6)
