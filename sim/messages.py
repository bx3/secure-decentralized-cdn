from enum import Enum
from collections import namedtuple

class GossipMessageType(Enum):
    GRAFT = 0
    PRUNE = 1
    LEAVE = 2
    IHAVE = 3
    IWANT = 4
    PX = 5
    TRANS = 6
    HEARTBEAT = 7

# other MessageType for Flood ...
# mtype, mid, src, dst, adv, len, payload = msg
Message = namedtuple('Message', ['mType', 'id', 'src', 'dst', 'adv', 'length', 'payload'])

# Graft = namedtuple('Graft', [''])
Heartbeat = namedtuple('Heartbeat', ['ihaves'])
IHave = namedtuple('IHave', ['msgs_id'])
IWant = namedtuple('IWant', ['msgs_id'])

