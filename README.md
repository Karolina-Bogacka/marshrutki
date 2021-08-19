To run this project, first install SUMO (Simulation Of Urban Mobility) with sumo-gui included. Set appropriate variable 
SUMO_HOME. Then, run simulateTaxi.py from directory marshrutki with two numerical arguments denoting the number of 
passengers and vehicles in the simulation.



To generate routes as appropriate for vehicles of type taxi according to SUMO guidelines, run:

python randomTrips.py -n config-smaller-berlin/osm.net.xml --trip-attributes="departLane=\"best\" departSpeed=\"max\" departPos=\"random\"" --
additional-file config-smaller-berlin/add.xml -o config-smaller-berlin/output-trips.xml -e 50 --validate