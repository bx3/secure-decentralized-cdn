from enum import Enum
from collections import namedtuple

class MessageType(Enum):
    GRAFT = 0
    PRUNE = 1
    JOIN  = 2
    LEAVE = 3
    IHAVE = 4
    IWANT = 5
    PRUNE_PEER = 6

Message = namedtuple('Message', ['mType', 'src', 'dst'])
