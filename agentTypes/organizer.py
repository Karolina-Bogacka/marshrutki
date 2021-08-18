from icecream import ic
from osbrain import Agent
from scipy.spatial import distance

from agentTypes.vehicle import MiniBusState


class Organizer(Agent):
    id = ""
    borders = []
    passenger_stops = {}
    reservations = {}
    taxis = {"PASSIVE": {},
             "TO_DISPATCH": {},
             "DRIVING_FULL": {},
             "DRIVING_NOT_FULL": {}
             }

    passengers = {
        "NO_REQUESTS": {},
        "PASSIVE": {},
        "WAITING": {},
        "DRIVING": {}
    }

    def after_init(self, id, edge_positions):
        ic(f"Organizer init {self.id}")
        self.id = id
        self.edge_positions = edge_positions

    def choose_taxi_to_dispatch(self, destination_edge, position, passenger_id):
        dest_pos = self.edge_positions[destination_edge]
        if self.taxis["PASSIVE"] or self.taxis["DRIVING_NOT_FULL"] or self.taxis["TO_DISPATCH"]:
            closest = None
            insert_orders = [0, 1]
            closest_distance = distance.euclidean(self.borders[0], self.borders[1])*2
            closest_len = 16
            available_taxis = self.taxis["PASSIVE"] | self.taxis["DRIVING_NOT_FULL"] | self.taxis["TO_DISPATCH"]
            for taxi in available_taxis:
                if len(self.passenger_stops[taxi]) == 0:
                    new_dist = distance.euclidean(position, available_taxis[taxi])
                    new_dist += distance.euclidean(dest_pos, available_taxis[taxi])
                    if new_dist <= closest_distance + closest_len*100:
                        closest_distance = new_dist
                        closest = taxi
                        closest_len = 0
                        insert_orders = [0, 1]
                else:
                    new_len = len(self.passenger_stops[taxi])
                    for i in range(0, len(self.passenger_stops[taxi])-1):
                        for j in range(i+1, len(self.passenger_stops[taxi])):
                            new_dist = (distance.euclidean(position, self.passenger_stops[taxi][i][1]) + distance.euclidean(available_taxis[taxi], position))/2
                            if i > 0:
                                new_dist = (distance.euclidean(position, self.passenger_stops[taxi][i][1]) + distance.euclidean(position, self.passenger_stops[taxi][i-1][1]))/2
                            if j == len(self.passenger_stops[taxi]):
                                new_dist += (distance.euclidean(dest_pos, self.passenger_stops[taxi][j][1])+distance.euclidean(available_taxis[taxi], dest_pos))/2
                            else:
                                new_dist += (distance.euclidean(dest_pos, self.passenger_stops[taxi][j][1])+ distance.euclidean(dest_pos, self.passenger_stops[taxi][j-1][1]))/2
                            if new_dist + new_len*100 <= closest_distance + closest_len*100:
                                closest_distance = new_dist
                                closest = taxi
                                closest_len = new_len
                                insert_orders = [i, j]
            self.passenger_stops[closest].insert(insert_orders[0], (passenger_id, position))
            self.passenger_stops[closest].insert(insert_orders[1], (passenger_id, dest_pos))
            order = [tup[0] for tup in self.passenger_stops[closest]]
            if closest in self.taxis["PASSIVE"]:
                val = self.taxis["PASSIVE"].pop(closest)
                self.taxis["TO_DISPATCH"][closest] = val
            elif closest in self.taxis["DRIVING_NOT_FULL"]:
                if closest in self.passenger_stops and len(self.passenger_stops[closest]) <= 16:
                    val = self.taxis["DRIVING_NOT_FULL"].pop(closest)
                    self.taxis["TO_DISPATCH"][closest] = val
            return closest, order
        else:
            return None, []

    def set_borders(self, borders):
        self.borders = borders

    def get_borders(self):
        return self.borders

    def set_drivers(self, drivers):
        self.drivers = drivers
        self.taxis["PASSIVE"] = drivers

    def get_drivers(self):
        return self.drivers

    def set_passengers(self, passengers):
        self.passengers = passengers

    def get_passengers(self):
        return self.passengers

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
            self.reply_dispatched_back(message)
        elif "Picked up" in message[0]:
            return self.reply_picked_up(message)
        elif "Delivered" in message[0]:
            return self.reply_delivered(message)
        else:
            return self.reply_vehicle_back(message)

    def reply_picked_up(self, message):
        self.send(self.id, ["Passenger picked up", message[1]], topic="Passenger_picked")
        for key in self.passenger_stops[message[2]]:
            if message[3].count(key) == 1:
                elements = [e for e in self.passenger_stops[message[2]] if e[0] == key]
                self.passenger_stops[message[2]].remove(elements[0])

    def reply_delivered(self, message):
        self.send(self.id, ["Passenger delivered", message[1]], topic="Passenger_picked")
        self.passenger_stops[message[2]] = [m for m in self.passenger_stops[message[2]] if m[0] in message[3]]
        if len(self.passenger_stops[message[2]])<=14 and message[2] in self.taxis["DRIVING_FULL"]:
            val = self.taxis["DRIVING_FULL"].pop(message[2])
            self.taxis["DRIVING_NOT_FULL"][message[2]] = val
        self.reservations.pop(message[1], None)

    def reply_dispatched_back(self, message):
        self.log_info(f"Taxi {message[1]} dispatched to {message[2]}")
        self.reservations[message[2]] = message[5]
        self.send(self.id, [message[2], message[5]], topic="Passenger_dispatched")
        if message[4] == MiniBusState.DRIVING_FULL and message[1] in self.taxis["TO_DISPATCH"]:
            val = self.taxis["TO_DISPATCH"].pop(message[1])
            self.taxis["DRIVING_FULL"][message[1]] = val
        elif message[4] == MiniBusState.DRIVING_NOT_FULL and message[1] in self.taxis["TO_DISPATCH"]:
            val = self.taxis["TO_DISPATCH"].pop(message[1])
            self.taxis["DRIVING_NOT_FULL"][message[1]] = val

    def reply_passenger_back(self, message):
        self.log_info(f"Find the right taxi for {message[0]}")
        taxi, order = self.choose_taxi_to_dispatch(message[1], message[4], message[0])
        if taxi:
            self.log_info(f"Found taxi for {message[0]} with id of {taxi}")
            self.send(self.id, [taxi, message[0], message[1], order], topic="Vehicle_subscribe")
            self.send(self.id, [message[0]], topic="Passenger_assigned")
        return f'Received request from {message[0]} travelling to {message[1]}'

    def reply_vehicle_back(self, message):
        for category in self.taxis:
            if message[0] in self.taxis[category]:
                self.taxis[category][message[0]] = message[1]
        return f'Received request from {message[0]} at position {message[1]}'
