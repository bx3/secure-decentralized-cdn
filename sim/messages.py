from enum import Enum
from collections import namedtuple

class GossipMessageType(Enum):
    GRAFT = 0
    PRUNE = 1
    JOIN  = 2
    LEAVE = 3
    IHAVE = 4
    IWANT = 5
    PRUNE_PEER = 6
    CONTENT = 7

# other MessageType for Flood ...
# last adv is flag for adversarial
Message = namedtuple('Message', ['mType', 'id', 'src', 'dst', 'adv'])
