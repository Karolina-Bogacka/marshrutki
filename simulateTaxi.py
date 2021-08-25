import argparse
import math
import os
import random
import sys
from functools import reduce
from operator import concat

import osbrain
import traci
from defusedxml import minidom
from icecream import ic
from osbrain import run_nameserver, run_agent
from sumolib.miscutils import getFreeSocketPort

from agentTypes.organizer import Organizer
from agentTypes.city_organizer import CityOrganizer
from agentTypes.passenger import Passenger, PassengerState
from agentTypes.vehicle import MiniBus
from utils import closest_divisors, check_boundaries


def assign_organizer(edge, position, organizers):
    pos = traci.simulation.convert2D(edge, position)
    for org in organizers:
        borders = org.get_borders()
        if check_boundaries(pos, borders):
            return org
    return None


def simulation_setup(pass_num, veh_num, org_num, port, generated_routes):
    divisors = closest_divisors(org_num)
    boundaries = traci.simulation.getNetBoundary()[1]
    difference = [math.floor(boundaries[0] / divisors[0]), math.floor(boundaries[1] / divisors[1])]

    start_end = [0, 0]
    new_end = [difference[0], difference[1]]
    generated, edges = read_generated_routes(generated_routes)
    lanes = traci.lane.getIDList()
    lengths = {traci.lane.getEdgeID(lane): traci.lane.getLength(lane) for lane in lanes}
    validated_lengths = {l: lengths[l] for l in lengths if l in edges}
    edge_positions = {key: traci.simulation.convert2D(key, int(value / 2)) for key, value in lengths.items()}

    city_org = run_agent(f'city-organizer', base=CityOrganizer, attributes=dict(port=port))
    city_org.after_init(f'city-organizer')

    organizers = []
    org_dict = {}
    indexes = divisors.copy()
    for o in range(org_num):
        organizer = run_agent(f'organizer-{o}', base=Organizer, attributes=dict(port=port))
        organizer.after_init(f'organizer-{o}', edge_positions=edge_positions)
        borders = [start_end.copy(), new_end.copy()]
        organizer.set_borders(borders)
        org_dict[f'organizer-{o}'] = borders
        addr = organizer.bind('SYNC_PUB', alias=f'organizer-{o}', handler=Organizer.reply_back)
        city_addr = city_org.bind('REP', alias=f'city-organizer-{o}', handler=CityOrganizer.shuffle_passenger)
        organizer.connect(city_addr, alias=f'city-organizer-{o}')
        organizer.set_city_addr(f'city-organizer-{o}')
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

    city_org.set_organizers(org_dict)

    passengers = {}
    passenger_positions = {}
    for i in range(pass_num):
        route = traci.route.getEdges(generated[-1 * i])
        position = random.randrange(0, math.floor(lengths[route[0]]))
        traci.person.add(f'person-{i}', route[0], position)
        traci.person.appendDrivingStage(f"person-{i}", route[-1], 'taxi')
        traci.person.appendWaitingStage(f"person-{i}", 7)
        passenger = run_agent(f'person-{i}', base=Passenger)

        org = assign_organizer(route[0], position, organizers)
        for o in organizers:
            address = o.get_address()
            passenger.connect(address, alias=o.get_id(),
                          handler={'Main': Passenger.read_subscription, 'Passenger_dispatched':
                              Passenger.update_dispatched, 'Passenger_assigned': Passenger.update_assigned,
                                   "Passenger_picked": Passenger.update_reservation})

        passenger.after_init(index=f'person-{i}', start=route[0], position1D=position,
                             position2D=traci.simulation.convert2D(route[0], position), destination=route[-1],
                             organizer=org.get_id())

        traci.person.subscribe(f'person-{i}', [traci.tc.VAR_POSITION])
        passengers[f'person-{i}'] = passenger
        passenger_positions[f'person-{i}'] = traci.simulation.convert2D(route[0], position)

    veh_positions = {}
    index = 0
    for org in organizers:
        vehicles = {}
        vehicle_positions = {}
        passenger_stops = {}
        for i in range(veh_num):
            vehicle = run_agent(f'vehicle-{index}', base=MiniBus)
            vehicle.after_init(f'vehicle-{index}', org.get_id())
            traci.vehicle.add(f'vehicle-{index}', generated[index], typeID="marshrutka", line="taxi")
            address = org.get_address()
            vehicle.connect(address, alias=org.get_id(),
                            handler={"Main": MiniBus.read_subscription, "Vehicle_subscribe": MiniBus.read_subscription})
            vehicle.each(5.0, MiniBus.handle_state)
            traci.vehicle.subscribe(f'vehicle-{index}', [traci.tc.VAR_POSITION])
            vehicles[f'vehicle-{index}'] = [0, 0]
            vehicle_positions[f'vehicle-{index}'] = vehicle
            passenger_stops[f'vehicle-{index}'] = []
            index += 1
        org.set_drivers(vehicles)
        org.set_passenger_stops(passenger_stops)
        org.each(3.0, Organizer.handle_updates)
        veh_positions = veh_positions | vehicle_positions

    return organizers, passengers, veh_positions, validated_lengths


def read_generated_routes(file):
    ids = []
    xmldoc = minidom.parse(file)
    itemlist = xmldoc.getElementsByTagName('trip')
    trips = [[item.attributes['from'].value, item.attributes['to'].value] for item in itemlist]
    edges = set(reduce(concat, trips))
    routes = [traci.simulation.findRoute(trip[0], trip[1], vType="marshrutka") for trip in trips]
    for i in range(len(routes)):
        id_route = f'route-taxi-{i}'
        traci.route.add(id_route, routes[i].edges)
        ids.append(id_route)
    return ids, edges


def update_driver(driver_key, drivers, picked_people, vehicle_positions):
    drivers[driver_key].update_picked(picked_people)
    drivers[driver_key].update_delivered(picked_people)
    if driver_key in vehicle_positions:
        drivers[driver_key].set_position(vehicle_positions[driver_key][66])
    if drivers[driver_key].check_to_dispatch():
        order = drivers[driver_key].get_order()
        reservations = drivers[driver_key].get_reservations()
        current_res = traci.person.getTaxiReservations()
        to_inform = []
        for passenger in set(order):
            if passenger not in reservations:
                id = [res.id for res in current_res if passenger in res.persons and res.state in [1, 2]]
                if id:
                    drivers[driver_key].set_reservation(passenger, id[0])
                    to_inform.append(passenger)
                else:
                    ic(passenger)
                    return
        reservations = drivers[driver_key].get_reservations()
        dispatch_order = [reservations[o] for o in order]
        try:
            traci.vehicle.dispatchTaxi(driver_key, dispatch_order)
        except traci.exceptions.TraCIException as e:
            ic(e)
        drivers[driver_key].set_order(order)
        drivers[driver_key].update_dispatched(to_inform)


def update_drivers(drivers):
    vehicle_positions = traci.vehicle.getAllSubscriptionResults()
    picked_up = traci.person.getTaxiReservations(8)
    picked_people = [res.persons[0] for res in picked_up]
    for driver_key in drivers:
        update_driver(driver_key, drivers, picked_people, vehicle_positions)


def update_passengers(passengers, edge_lengths):
    passenger_positions = traci.person.getAllSubscriptionResults()
    for pass_key in passengers:
        if pass_key in passenger_positions:
            passengers[pass_key].set_position(passenger_positions[pass_key][66])
        if passengers[pass_key].get_state() == PassengerState.NO_REQUESTS:
            if traci.person.getRemainingStages(pass_key) == 1:
                destination = random.choice(list(edge_lengths.keys()))
                traci.person.appendDrivingStage(pass_key, destination, 'taxi')
                traci.person.appendWaitingStage(pass_key, 7)
                passengers[pass_key].spawn_new_request(destination)


def update_organizers(organizers):
    for o in organizers:
        o.handle_updates()


def simulate(pass_num, veh_num, org_num=1, generated_routes='config-smaller-berlin/output-trips.xml'):
    ns = run_nameserver()
    port = getFreeSocketPort()
    sumoBinary = "sumo-gui"
    sumoCmd = [sumoBinary, "-c",
               r"config-smaller-berlin/osm.sumocfg", "--num-clients", "1", "--device.taxi.dispatch-algorithm", "traci",
               "--device.taxi.idle-algorithm", "stop", "--device.rerouting.explicit", "marshrutka"]
    traci.start(sumoCmd, port=port)

    organizers, passengers, vehicles, edges = simulation_setup(pass_num, veh_num, org_num, port, generated_routes)

    for passenger in passengers:
        passengers[passenger].each(5.0, Passenger.handle_state)

    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        update_drivers(vehicles)
        update_passengers(passengers, edges)
        update_organizers(organizers)
        step += 1
    traci.close(False)
    ns.shutdown()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    osbrain.config['SERIALIZER'] = 'raw'

    parser = argparse.ArgumentParser()
    parser.add_argument('vehicles', type=int,
                        help='number of vehicles for the simulation (for each organizer)')
    parser.add_argument('passengers', type=int,
                        help='number of passengers for the whole simulation')
    parser.add_argument('organizers', type=int,
                        help='number of passengers for the simulation')

    # parse the arguments
    args = parser.parse_args()
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("please declare environment variable 'SUMO_HOME'")
    simulate(args.passengers, args.vehicles, args.organizers)
