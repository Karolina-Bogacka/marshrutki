from icecream import ic
from osbrain import Agent
from scipy.spatial import distance

from agentTypes.vehicle import MiniBusState
from utils import combined_distance, check_boundaries


class Organizer(Agent):
    id = ""
    borders = []
    passenger_stops = {}
    reservations = {}
    assigned = []
    picked_or_delivered = []
    to_subscribe = {}
    dispatched = []
    city_org = 'city-organizer'
    taxis = {"PASSIVE": {},
             "TO_DISPATCH": {},
             "DRIVING_FULL": {},
             "DRIVING_NOT_FULL": {}
             }

    def after_init(self, index, edge_positions):
        ic(f"Organizer init {index}")
        self.id = index
        self.edge_positions = edge_positions

    def handle_updates(self):
        self.send(self.id, ["Passenger delivered", self.picked_or_delivered], topic="Passenger_picked")
        self.picked_or_delivered = []
        to_dispatch = {to: self.reservations[to] for to in self.dispatched}
        self.send(self.id, to_dispatch, topic="Passenger_dispatched")
        self.dispatched = []
        self.send(self.id, self.assigned, topic="Passenger_assigned")
        self.assigned = []
        self.send(self.id, self.to_subscribe, topic="Vehicle_subscribe")
        self.to_subscribe = {}

    def choose_taxi(self, destination_edge, position, passenger_id):
        dest_pos = self.edge_positions[destination_edge]
        available_taxis = self.taxis["PASSIVE"] | self.taxis["DRIVING_NOT_FULL"] | self.taxis["TO_DISPATCH"]
        if available_taxis:
            closest = None
            insert_orders = [0, 1]
            closest_distance = distance.euclidean(self.borders[0], self.borders[1]) * 2
            closest_len = 16
            for taxi in available_taxis:
                if len(self.passenger_stops[taxi]) == 0:
                    new_dist = combined_distance(available_taxis[taxi], position, dest_pos)
                    new_dist += combined_distance(position, dest_pos, available_taxis[taxi])
                    if new_dist <= closest_distance + closest_len * 50:
                        closest_distance = new_dist
                        closest = taxi
                        closest_len = 0
                        insert_orders = [0, 1]
                else:
                    new_len = len(self.passenger_stops[taxi])
                    for i in range(0, len(self.passenger_stops[taxi]) - 1):
                        for j in range(i + 1, len(self.passenger_stops[taxi])):
                            if i > 0:
                                new_dist = combined_distance(self.passenger_stops[taxi][i][1], position,
                                                             self.passenger_stops[taxi][i - 1][1])
                            else:
                                new_dist = combined_distance(self.passenger_stops[taxi][i][1], position,
                                                             available_taxis[taxi])
                            if j == len(self.passenger_stops[taxi]):
                                new_dist += combined_distance(self.passenger_stops[taxi][j][1], dest_pos,
                                                              available_taxis[taxi])
                            else:
                                new_dist += combined_distance(self.passenger_stops[taxi][j][1], dest_pos,
                                                              self.passenger_stops[taxi][j - 1][1])
                            if new_dist + new_len * 50 <= closest_distance + closest_len * 50:
                                closest_distance = new_dist
                                closest = taxi
                                closest_len = new_len
                                insert_orders = [i, j]
            self.passenger_stops[closest].insert(insert_orders[0], (passenger_id, position))
            self.passenger_stops[closest].insert(insert_orders[1], (passenger_id, dest_pos))
            order = [tup[0] for tup in self.passenger_stops[closest]]
            self.mark_to_dispatch(closest)
            return closest, order
        else:
            return None, []

    def mark_to_dispatch(self, closest):
        if closest in self.taxis["PASSIVE"]:
            val = self.taxis["PASSIVE"].pop(closest)
            self.taxis["TO_DISPATCH"][closest] = val
        elif closest in self.taxis["DRIVING_NOT_FULL"]:
            if closest in self.passenger_stops and len(self.passenger_stops[closest]) <= 16:
                val = self.taxis["DRIVING_NOT_FULL"].pop(closest)
                self.taxis["TO_DISPATCH"][closest] = val

    def set_borders(self, borders):
        self.borders = borders

    def get_borders(self):
        return self.borders

    def set_drivers(self, drivers):
        self.drivers = drivers
        self.taxis["PASSIVE"] = drivers

    def get_drivers(self):
        return self.drivers

    def set_reservations(self, reservations):
        self.reservations = reservations

    def get_reservations(self):
        return self.reservations

    def set_passenger_stops(self, passenger_stops):
        self.passenger_stops = passenger_stops

    def get_passenger_stops(self):
        return self.passenger_stops

    def set_address(self, address):
        self.address = address

    def get_address(self):
        return self.address

    def set_id(self, id):
        self.id = id

    def get_id(self):
        return self.id

    def reply_back(self, message):
        if "person" in message[0]:
            return self.reply_passenger_back(message)
        elif "Dispatched" in message[0]:
            self.reply_dispatched(message)
        elif "Picked up" in message[0]:
            return self.reply_picked_up(message)
        elif "Delivered" in message[0]:
            return self.reply_delivered(message)
        else:
            return self.reply_vehicle_back(message)

    def reply_picked_up(self, message):
        self.picked_or_delivered.append(message[1])
        for key in self.passenger_stops[message[2]]:
            if message[3].count(key) == 1:
                elements = [e for e in self.passenger_stops[message[2]] if e[0] == key]
                self.passenger_stops[message[2]].remove(elements[0])

    def reply_delivered(self, message):
        self.picked_or_delivered.append(message[1])
        self.passenger_stops[message[2]] = [m for m in self.passenger_stops[message[2]] if m[0] in message[3]]
        if len(self.passenger_stops[message[2]]) <= 14 and message[2] in self.taxis["DRIVING_FULL"]:
            val = self.taxis["DRIVING_FULL"].pop(message[2])
            self.taxis["DRIVING_NOT_FULL"][message[2]] = val
        self.reservations.pop(message[1], None)

    def reply_dispatched(self, message):
        self.log_info(f"Taxi {message[1]} dispatched to {message[2]}")
        self.reservations[message[2]] = message[5]
        self.dispatched.append(message[2])
        if message[4] == MiniBusState.DRIVING_FULL and message[1] in self.taxis["TO_DISPATCH"]:
            val = self.taxis["TO_DISPATCH"].pop(message[1])
            self.taxis["DRIVING_FULL"][message[1]] = val
        elif message[4] == MiniBusState.DRIVING_NOT_FULL and message[1] in self.taxis["TO_DISPATCH"]:
            val = self.taxis["TO_DISPATCH"].pop(message[1])
            self.taxis["DRIVING_NOT_FULL"][message[1]] = val

    def set_city_addr(self, city_addr):
        self.city_org = city_addr

    def reply_passenger_back(self, message):
        if not check_boundaries(message[4], self.borders):
            self.send(self.city_org, [message[4], message[0], self.id])
            reply = self.recv(self.city_org)
            if reply != self.id:
                return [False, reply]
        self.log_info(f"Find the right taxi for {message[0]}")
        taxi, order = self.choose_taxi(message[1], message[4], message[0])
        if taxi:
            self.log_info(f"Found taxi for {message[0]} with id of {taxi}")
            stop_edges = self.to_subscribe[taxi][0] if taxi in self.to_subscribe else {}
            stop_edges[message[0]] = message[1]
            self.to_subscribe[taxi] = [stop_edges, order]
            self.assigned.append(message[0])
        return f'Received correct request from {message[0]} travelling to {message[1]}'

    def reply_vehicle_back(self, message):
        for category in self.taxis:
            if message[0] in self.taxis[category]:
                self.taxis[category][message[0]] = message[1]
        return f'Received request from {message[0]} at position {message[1]}'
