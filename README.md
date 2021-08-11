Things to do for the project:
- I'll be using osBrain and sumo, so that's settled
- Our project should visualize a system of "marshrutka" agents, clients and holonic schedulers
- that means three types of successful agents and a few methods for each, for sure
- these should be in my old presentation
- I should write an email about it tomorrow or today, to ask about it maybe, in theory. But should I?
On the one hand using sumo-gui means using gui, means maybe slowing it down; on the other hand, maybe
  I can just use sumo with no gui?
  - should I get a database? I would wait with that, I think
    
- For the simple version of that, I should probably also have a script that would visualize n people and n cars 
with random targets, first in the one neighborhood, then outside of it later.
  
- also, theoretically I should the type "taxi" would probably be the most fitting for marshrutkas, and it would be nice to 
  use it for comparison - but I should be able to use holons to steer the cars, so more baseline solutions will probably 
  be needed.
  
- I can probably use the right options with randomTrips to generate trips for taxis and validate them, and take the trips and assign them to passengers
I guess
  
***
  
- what to do with the multi client part? I can try to run them from different processes, although I would have to think a bit about how to do that, ot I coul
use one connection and kind of update most agents based on what they would know in each simulation step. For example, the vehicles
  would know vehicle position, the passengers passenger position (and we can store this objects and update them), and organizers
  should be able to (somehow) connect and dispatch taxis, so that's nice. we could ensure in this way that specific parts have only specific 
  access. also, I wonder how subscriptions work in traci and how to deal with dispatching. I guess it's all a thing I can deal with from the main loop
  right now?
  
- I guess most of this stuff I can do now and add specification of what goes where later, for example move specific parts to organizers, and counting 
lanes and edges at the beginning was planned anyways.
  
python randomTrips.py -n config-smaller-berlin/osm.net.xml --trip-attributes="departLane=\"best\" departSpeed=\"max\" departPos=\"random\"" --
additional-file config-smaller-berlin/add.xml -o config-smaller-berlin/output-trips.xml -e 50 --validate


- ch