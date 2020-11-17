from enum import Enum

# network
N_PUB = 90
N_LURK = 10
N_DEGREE = 20

N_SYBIL = 0
ATTACK_DEG = 100

RTT = 100 # millisecond
LINK_LATENCY = 50 # millisecond
MILLISEC_PER_ROUND = LINK_LATENCY
NETWORK_QUEUE_LIM = 100
BANDWIDTH = 24*8*1e6 # 24 MB per sec

# mesh
OVERLAY_D = 8
OVERLAY_DLO = 6
OVERLAY_DHI = 12

OVERLAY_DSCORE = 6
OVERLAY_DLAZY = 12
HEARTBEAT = 1e3/MILLISEC_PER_ROUND # 1 sec <=> 20 round

TIMEOUT = 4 # round

D_OUT = 8 # min outbound connection per peer

GOSSIP_FACTOR = 0.25

NUM_TRANS_PER_SEC = 120
TRANS_SIZE = 2e3 # bytes

CTRL_MSG_LEN = 0

INIT_NUM_KNOWN_PEER = OVERLAY_D*2

assert(N_PUB + N_LURK > OVERLAY_D)

class NodeType(Enum):
    PUB = 0
    LURK = 1
    SYBIL = 2
    BOOTSTRAP = 3 

# class NodeAttr:
    # def __init__(self, node_type):
        # self.connections = [] # active other nodes
        # self.role = node_type

# Peer Score Parameters
# from Gossipsub V1.1 evaluation report
TOPIC_WEIGHT = 0.25
TIME_IN_MESH_WEIGHT = 0.0027
TIME_IN_MESH_QUANTUM = "1s"
TIME_IN_MESH_CAP = 3600.0
FIRST_MESSAGE_DELIVERIES_WEIGHT = 0.664
FIRST_MESSAGE_DELIVERIES_DECAY = 0.9916
FIRST_MESSAGE_DELIVERIES_CAP = 1500.0
MESH_MESSAGE_DELIVERIES_WEIGHT = -0.25
MESH_MESSAGE_DELIVERIES_DECAY = 0.997
MESH_MESSAGE_DELIVERIES_CAP = 400.0
MESH_MESSAGE_DELIVERIES_THRESHOLD = 10.0
MESH_MESSAGE_DELIVERIES_ACTIVATION = "1m"
MESH_MESSAGE_DELIVERY_WINDOW = "5ms"
MESH_FAILURE_PENALTY_WEIGHT = -0.25
MESH_FAILURE_PENALTY_DECAY = 0.997
INVALID_MESSAGE_DELIVERIES_WEIGHT = -99.0
INVALID_MESSAGE_DELIVERIES_DECAY = 0.9994
