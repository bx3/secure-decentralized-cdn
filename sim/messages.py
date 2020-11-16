from enum import Enum
from collections import namedtuple

class MessageType(Enum):
    GRAFT = 0
    PRUNE = 1
    LEAVE = 2
    IHAVE = 3
    IWANT = 4
    PX = 5
    TRANS = 6
    HEARTBEAT = 7

class Direction(Enum):
    Incoming = 0
    Outgoing = 1

# other MessageType for Flood ...
# mtype, mid, src, dst, adv, len, payload = msg
Message = namedtuple('Message', ['mType', 'id', 'src', 'dst', 'adv', 'length', 'payload'])

# Graft = namedtuple('Graft', [''])
Heartbeat = namedtuple('Heartbeat', ['null'])
IHave = namedtuple('IHave', ['msgs_id']) # msgs_id is a list of msg id
IWant = namedtuple('IWant', ['msgs_id'])
Prune = namedtuple('Prune', ['null']) 
PX = namedtuple('PX', ['peers']) # peers is a list of node id for other to add

# example
# payload = PX([11,3])
# msg = Message(MessageType.PX, 0, 1, 2, False, 100, payload)
# print('peers', msg.payload.peers)

