from enum import Enum
# define 
N_PUB = 90
N_LURK = 10
N_DEGREE = 20

N_SYBIL = 0
ATTACK_DEG = 100

OVERLAY_D = 8
OVERLAY_DLO = 6
OVERLAY_DHI = 12

OVERLAY_DSCORE = 6
OVERLAY_DLAZY = 12

NETWORK_QUEUE_LIM = 100

HEARTBEAT = 10 # round

class NodeType(Enum):
    PUB = 0
    LURK = 1
    SYBIL = 2

# class NodeAttr:
    # def __init__(self, node_type):
        # self.connections = [] # active other nodes
        # self.role = node_type


