import math
import os
from functools import reduce
from operator import concat

import osbrain
import traci
import sys
import argparse

from defusedxml import minidom
import random

from icecream import ic
from osbrain import run_nameserver, run_agent
from sumolib.miscutils import getFreeSocketPort
from agentTypes.organizer import Organizer
from agentTypes.passenger import Passenger, PassengerState
from agentTypes.vehicle import MiniBus
from utils import closest_divisors


def assign_organizer(edge, position, subject, organizers):
    pos = traci.simulation.convert2D(edge, position)
    for org in organizers:
        borders = org.get_borders()
        if pos[0] >= borders[0][0] and pos[1] >= borders[0][1]:
            if pos[0] < borders[1][0] and pos[1] < borders[1][1]:
                passes = org.get_passengers()
                passes['NO_REQUESTS'][subject.get_id()] = pos
                org.set_passengers(passes)
                return org
    return None

def simulation_setup(pass_num, veh_num, org_num, port, generated_routes):
    divisors = closest_divisors(org_num)
    boundaries = traci.simulation.getNetBoundary()[1]
    difference = [int(boundaries[0] / divisors[0]), int(boundaries[1] / divisors[1])]

    start_end = [0, 0]
    new_end = [difference[0], difference[1]]
    generated, edges = read_generated_routes(generated_routes)
    lanes = traci.lane.getIDList()
    lengths = {traci.lane.getEdgeID(lane): traci.lane.getLength(lane) for lane in lanes}
    validated_lengths = {l:lengths[l] for l in lengths if l in edges}
    ic(validated_lengths)
    edge_positions = {key: traci.simulation.convert2D(key, int(value / 2)) for key, value in lengths.items()}

    organizers = []
    indexes = divisors.copy()
    for o in range(org_num):
        organizer = run_agent(f'organizer-{o}', base=Organizer, attributes=dict(port=port))
        organizer.after_init(f'organizer-{o}', edge_positions=edge_positions)
        organizer.set_borders([start_end, new_end])
        addr = organizer.bind('SYNC_PUB', alias=f'organizer-{o}', handler=Organizer.reply_back)
        organizer.set_address(addr)
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

    passengers = {}
    passenger_positions = {}
    for i in range(pass_num):
        route = traci.route.getEdges(generated[-1 * i])
        position = random.randrange(0, math.floor(lengths[route[0]]))
        traci.person.add(f'person-{i}', route[0], position)
        traci.person.appendDrivingStage(f"person-{i}", route[-1], 'taxi')
        traci.person.appendWaitingStage(f"person-{i}", 5)
        passenger = run_agent(f'person-{i}', base=Passenger)

        org = assign_organizer(route[0], position, passenger, organizers)
        address = org.get_address()
        passenger.connect(address, alias=org.get_id(),
                          handler={'Main': Passenger.read_subscription, 'Passenger_dispatched':
                                   Passenger.update_dispatched, 'Passenger_assigned': Passenger.update_assigned,
                                   "Passenger_picked": Passenger.update_reservation})
        passenger.after_init(id=f'person-{i}', start=route[0], position1D=position,
                             position2D=traci.simulation.convert2D(route[0], position), destination=route[-1],
                             organizer=org.get_id())
        passenger.each(3.0, Passenger.handle_state)

        traci.person.subscribe(f'person-{i}', [traci.tc.VAR_POSITION])
        passengers[f'person-{i}'] = passenger
        passenger_positions[f'person-{i}'] = traci.simulation.convert2D(route[0], position)

    vehicles = {}
    vehicle_positions = {}
    passenger_stops = {}
    for i in range(veh_num):
        vehicle = run_agent(f'vehicle-{i}', base=MiniBus)
        vehicle.after_init(f'vehicle-{i}', organizers[0].get_id())
        traci.vehicle.add(f'vehicle-{i}', generated[i], typeID="marshrutka", line="taxi")
        address = organizers[0].get_address()
        vehicle.connect(address, alias=organizers[0].get_id(),
                        handler={"Main": MiniBus.read_subscription, "Vehicle_subscribe": MiniBus.read_subscription})
        vehicle.each(3.0, MiniBus.handle_state)
        traci.vehicle.subscribe(f'vehicle-{i}', [traci.tc.VAR_POSITION])
        vehicles[f'vehicle-{i}'] = [0, 0]
        vehicle_positions[f'vehicle-{i}'] = vehicle
        passenger_stops[f'vehicle-{i}'] = []
    organizers[0].set_drivers(vehicles)
    organizers[0].set_passenger_stops(passenger_stops)

    return organizers, passengers, vehicle_positions, validated_lengths


def read_generated_routes(file):
    ids = []
    xmldoc = minidom.parse(file)
    itemlist = xmldoc.getElementsByTagName('trip')
    trips = [[item.attributes['from'].value, item.attributes['to'].value] for item in itemlist]
    edges = set(reduce(concat,trips))
    ic(edges)
    routes = [traci.simulation.findRoute(trip[0], trip[1], vType="marshrutka") for trip in trips]
    for i in range(len(routes)):
        id_route = f'route-taxi-{i}'
        traci.route.add(id_route, routes[i].edges)
        ids.append(id_route)
    return ids, edges


def update_drivers(drivers):
    vehicle_positions = traci.vehicle.getAllSubscriptionResults()
    picked_up = traci.person.getTaxiReservations(8)
    picked_people = [res.persons[0] for res in picked_up]
    for driver_key in drivers:
        drivers[driver_key].update_picked(picked_people)
        drivers[driver_key].update_delivered(picked_people)
        if driver_key in vehicle_positions:
            drivers[driver_key].set_position(vehicle_positions[driver_key][66])
        if drivers[driver_key].check_to_dispatch():
            order = drivers[driver_key].get_order()
            reservations = drivers[driver_key].get_reservations()
            ic(reservations)
            ic(order)
            to_inform = []
            for passenger in set(order):
                if passenger not in reservations:
                    id = [res.id for res in traci.person.getTaxiReservations() if passenger in res.persons and res.state in [1, 2]]
                    if id:
                        ic(id)
                        drivers[driver_key].set_reservation(passenger, id[0])
                        to_inform.append(passenger)
            reservations = drivers[driver_key].get_reservations()
            ic(reservations)
            ic(order)
            dispatch_order = [reservations[o] for o in order]
            traci.vehicle.dispatchTaxi(driver_key, dispatch_order)
            drivers[driver_key].update_dispatched(to_inform)


def update_passengers(passengers, edge_lengths):
    passenger_positions = traci.person.getAllSubscriptionResults()
    for pass_key in passengers:
        if pass_key in passenger_positions:
            passengers[pass_key].set_position(passenger_positions[pass_key][66])
        if passengers[pass_key].get_state() == PassengerState.NO_REQUESTS:
            destination = random.choice(list(edge_lengths.keys()))
            traci.person.appendDrivingStage(pass_key, destination, 'taxi')
            passengers[pass_key].spawn_new_request(destination)



def update_organizers(organizers):
    # TODO: add updating and swapping the organizers when needed
    pass


def simulate(pass_num, veh_num, org_num=1, generated_routes='config-smaller-berlin/output-trips.xml'):
    ns = run_nameserver()
    port = getFreeSocketPort()
    sumoBinary = "sumo-gui"
    sumoCmd = [sumoBinary, "-c",
               r"config-smaller-berlin/osm.sumocfg", "--num-clients", "1", "--device.taxi.dispatch-algorithm", "traci",
               "--device.taxi.idle-algorithm", "randomCircling", "--device.rerouting.explicit", "marshrutka"]
    traci.start(sumoCmd, port=port)

    organizers, passengers, vehicles, edge_lengths = simulation_setup(pass_num, veh_num, org_num, port, generated_routes)

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        update_drivers(vehicles)
        update_passengers(passengers, edge_lengths)
        update_organizers(organizers)
        # reservations = traci.person.getTaxiReservations()
        # for i in range(len(reservations)):
        #    if reservations[i].state == 1:
        #        traci.vehicle.dispatchTaxi(f'vehicle-{i}', [reservations[i].id])
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
    simulate(args.passengers, args.vehicles, 1)
